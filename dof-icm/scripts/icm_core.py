"""Core library for the DOF-ICM file-based agent.

Shared by two entry points:

- ``scripts/run_icm_agent.py`` — the CLI used for benchmarks/eval runs.
- ``web/icm_executor.py`` — the file-backed executor that powers the
  human-evaluation web UI (adapted from CodeandoGuadalajara/dof-rag).

The agent reads the ICM workspace context (CLAUDE.md, CONTEXT.md, stage
contracts, skill files) and answers a question using file-based tools
(grep_corpus, read_file, list_year, list_section) over the plain-markdown
corpus. No embeddings, no DB, no server — the corpus is the state and the
tools talk to the filesystem.

Everything here is workspace-parameterised so the same module can drive any
checkout of the workspace (the corpus folder travels with the workspace).
"""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

# Default workspace: dof-icm/ (parent of scripts/).
WORKSPACE = Path(__file__).resolve().parent.parent

# Category-aware turn budget: easy/medium stay fast; the hard tier
# (multi-doc, negative-premise) legitimately needs more reads.
MAX_TURNS_BY_CATEGORY = {
    "multi_document": 14,
    "negative_false_premise": 12,
    "temporal_transitorio": 12,
    "cross_reference": 10,
}
DEFAULT_MAX_TURNS = 8


def max_turns_for(qid: str, category: str) -> int:
    override = os.environ.get("DOF_MAX_TURNS")
    if override:
        return int(override)
    return MAX_TURNS_BY_CATEGORY.get(category, DEFAULT_MAX_TURNS)


def load_text(path: Path, limit: int = 12_000) -> str:
    if not path.exists():
        return f"[missing: {path}]"
    return path.read_text(encoding="utf-8")[:limit]


# Context budget: LM Studio / Qwen run on a fixed window (32k-64k). We estimate
# tokens per message and COMPACT the conversation before it overflows, so a
# long tool loop never crashes the local server. Env-tunable:
#   DOF_CTX_WINDOW_TOKENS  total context window (default 56000, ~87% of 64k)
#   DOF_CTX_COMPACT_AT     compact when estimated use passes this (default 0.60)
#   DOF_TOOL_RESULT_CHARS  cap chars per tool result (default 24000)
CTX_WINDOW = int(os.environ.get("DOF_CTX_WINDOW_TOKENS", "56000"))
CTX_COMPACT_AT = float(os.environ.get("DOF_CTX_COMPACT_AT", "0.60"))
TOOL_RESULT_CHARS = int(os.environ.get("DOF_TOOL_RESULT_CHARS", "24000"))


def tool_schemas() -> list[dict]:
    return [
        {
            "type": "function",
            "function": {
                "name": "list_year",
                "description": "List the DOF index for a publication year: total docs, per-month counts, and a few sample titles (corpus/index/by-year-YYYY.md).",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "year": {"type": "integer", "description": "4-digit year, e.g. 2025"}
                    },
                    "required": ["year"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "list_section",
                "description": "List the MAT or VES section index (corpus/index/by-section-*.md).",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "section": {"type": "string", "enum": ["MAT", "VES"]}
                    },
                    "required": ["section"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "search_titles",
                "description": "FAST: grep the full title index of a year for a term. Returns all matching relpaths with titles. Use this FIRST to locate documents by title/institution keyword. Then read_file the best match.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "pattern": {"type": "string", "description": "grep regex, case-insensitive, e.g. 'salarios m.nimos' or 'CONASAMI' or 'tipo de cambio'"},
                        "year": {"type": "string", "description": "Optional: restrict to a 4-digit year, e.g. 2025"},
                        "max_results": {"type": "integer", "description": "Max matches to return (default 10)"}
                    },
                    "required": ["pattern"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "grep_corpus",
                "description": "Grep the markdown corpus CONTENT for a term. SLOWER than search_titles — only use when the title index has no match and you must search document bodies. ALWAYS scope by year (and month if known). Returns matching files with hit counts and first-match snippets.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "pattern": {"type": "string", "description": "grep regex, e.g. 'salario m.nimo'"},
                        "year": {"type": "string", "description": "Required: 4-digit year subfolder, e.g. 2025"},
                        "month": {"type": "string", "description": "Optional: 2-digit month subfolder, e.g. 12"},
                        "section": {"type": "string", "description": "Optional: MAT or VES"},
                        "max_results": {"type": "integer", "description": "Max files to return (default 10)"}
                    },
                    "required": ["pattern", "year"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "read_file",
                "description": "Read a corpus markdown file (relpath from corpus/ root, e.g. 2025/12/09122025/MAT/006_DOF_20251209_MAT_5775533.md). Optionally a line range.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "relpath": {"type": "string", "description": "Path relative to corpus/"},
                        "start_line": {"type": "integer"},
                        "end_line": {"type": "integer"}
                    },
                    "required": ["relpath"],
                },
            },
        },
    ]


def _tool_label(name: str, args: dict) -> str:
    """Short human-readable label for a tool call (for the UI timeline)."""
    if name == "search_titles":
        scope = f" en {args.get('year')}" if args.get("year") else ""
        return f"Buscar títulos: «{args.get('pattern', '')}»{scope}"
    if name == "grep_corpus":
        month = f"/{args.get('month')}" if args.get("month") else ""
        section = f" {args.get('section')}" if args.get("section") else ""
        return (
            f"Buscar en el cuerpo: «{args.get('pattern', '')}»"
            f" en {args.get('year', '')}{month}{section}"
        )
    if name == "read_file":
        rel = args.get("relpath", "")
        if args.get("start_line") or args.get("end_line"):
            return f"Leer documento: {rel} (líneas {args.get('start_line', 1)}–{args.get('end_line', 'fin')})"
        return f"Leer documento: {rel}"
    if name == "list_year":
        return f"Índice por año: {args.get('year')}"
    if name == "list_section":
        return f"Índice por sección: {args.get('section')}"
    return f"{name}({str(args)[:80]})"


def call_tool(workspace: Path, name: str, args: dict) -> dict:
    corpus = workspace / "corpus"
    index = corpus / "index"
    if name == "list_year":
        p = index / f"by-year-{args['year']}.md"
        return {"ok": True, "content": load_text(p)}
    if name == "list_section":
        p = index / f"by-section-{args['section']}.md"
        return {"ok": True, "content": load_text(p)}
    if name == "search_titles":
        year = args.get("year")
        if year:
            paths = [index / f"titles-{year}.md"]
        else:
            paths = sorted(index.glob("titles-*.md"))
        pattern = args["pattern"]
        max_res = int(args.get("max_results", 10))
        out: list[dict] = []
        for p in paths:
            if not p.exists():
                continue
            try:
                # no -m1: later matches (later dates) in the same file must
                # also be returned
                proc = subprocess.run(
                    ["grep", "-iE", pattern, str(p)],
                    capture_output=True, text=True, timeout=30,
                )
            except subprocess.TimeoutExpired:
                continue
            for line in proc.stdout.splitlines():
                if not line.strip():
                    continue
                rel, _, title = line.partition("\t")
                out.append({"relpath": rel, "title": title.strip()[:400]})
        # rank: substantive DOF docs (not *_AVISO_* notices) first, and most
        # RECENT first (2026 before 2024), matching the prompt's "anchor on
        # as_of, search recent years first" guidance. relpath is
        # YYYY/MM/DD/SECTION/..., so negating year/month/day sorts newest up.
        def _rank(m: dict) -> tuple:
            rel = m["relpath"]
            return (
                "_AVISO_" in rel,
                -int(rel[0:4]),
                -int(rel[5:7]),
                -int(rel[8:10]),
            )

        out.sort(key=_rank)
        return {
            "ok": True,
            "content": json.dumps(out[:max_res], ensure_ascii=False),
        }
    if name == "grep_corpus":
        base = corpus
        if args.get("year"):
            base = base / str(args["year"])
        if args.get("month"):
            base = base / args["month"]
        if args.get("section"):
            base = base / args["section"]
        if not base.exists():
            return {"ok": False, "error": f"path not found: {base.relative_to(corpus)}"}
        pattern = args["pattern"]
        max_res = int(args.get("max_results", 10))
        try:
            proc = subprocess.run(
                ["grep", "-rilE", "--include=*.md", pattern, str(base)],
                capture_output=True, text=True, timeout=60,
            )
            files = [line for line in proc.stdout.splitlines() if line.strip()][:max_res]
            out = []
            for f in files:
                fp = Path(f)
                rel = fp.relative_to(corpus).as_posix()
                # first-match snippet with line number
                sp = subprocess.run(
                    ["grep", "-inm1", "-E", pattern, str(fp)],
                    capture_output=True, text=True, timeout=30,
                )
                snippet = sp.stdout.strip().splitlines()[0] if sp.stdout.strip() else ""
                out.append({"relpath": rel, "snippet": snippet[:300]})
            return {"ok": True, "content": json.dumps(out, ensure_ascii=False)}
        except subprocess.TimeoutExpired:
            return {"ok": False, "error": "grep timed out"}
    if name == "read_file":
        rel = args["relpath"]
        p = corpus / rel
        if not p.exists():
            return {"ok": False, "error": f"not found: {rel}"}
        text = p.read_text(encoding="utf-8", errors="replace")
        lines = text.splitlines()
        start = int(args.get("start_line", 1)) - 1
        end = int(args.get("end_line", len(lines)))
        if end > len(lines):
            end = len(lines)
        chunk = "\n".join(lines[start:end])

        # Long docs: return a heading OUTLINE (with line numbers) + the
        # requested section, so the agent can jump straight to e.g. the
        # Transitorios instead of chunk-reading a 1,900-line decree.
        if len(lines) > 400:
            heads = []
            for i, ln in enumerate(lines, 1):
                s = ln.strip()
                if s.startswith("#"):
                    heads.append(f"l{i}: {s[:110]}")
                if len(heads) > 60:
                    break
            if args.get("start_line") or args.get("end_line"):
                # explicit range: just return it
                return {
                    "ok": True,
                    "content": f"# {rel} (lines {start+1}-{end}, total {len(lines)})\n" + chunk,
                }
            # no range: return outline + first 200 lines
            outline = "\n".join(heads) if heads else "(no markdown headings)"
            return {
                "ok": True,
                "content": (
                    f"# {rel} ({len(lines)} lines). HEADING OUTLINE (line numbers "
                    f"refer to read_file start_line/end_line):\n{outline}\n\n"
                    f"--- first 200 lines ---\n" + "\n".join(lines[:200])
                ),
            }
        return {
            "ok": True,
            "content": f"# {rel} (lines {start+1}-{end}, total {len(lines)})\n" + chunk,
        }
    return {"ok": False, "error": f"unknown tool {name}"}


def build_system_prompt(workspace: Path, question: str, meta: str = "") -> str:
    def layer(*parts: str) -> Path:
        return workspace.joinpath(*parts)

    return f"""{load_text(layer("CLAUDE.md"))}

{load_text(layer("CONTEXT.md"))}

--- STAGE 01 CONTRACT (run this first) ---
{load_text(layer("stages", "01-locate", "CONTEXT.md"))}

Retrieval skill:
{load_text(layer("skills", "dof-retrieval", "SKILL.md"))}

Citation format:
{load_text(layer("stages", "01-locate", "references", "citation-format.md"))}

--- STAGE 02 CONTRACT (run after stage 01) ---
{load_text(layer("stages", "02-verify", "CONTEXT.md"))}

Answer quality:
{load_text(layer("stages", "02-verify", "references", "answer-quality.md"))}

--- TASK ---
Answer the following question about Mexican federal law using the DOF corpus
(2024-2026). Run stage 01 (locate candidate docs using the tools), then stage
02 (read the candidates and produce a cited answer). Every factual claim must
cite the document relpath and line range.

=== EFFICIENCY RULES (follow strictly — you have a small tool budget) ===
1. Prefer search_titles over grep_corpus: titles carry institution + topic, so
   most questions resolve in ONE search_titles call. Use grep_corpus only for
   body-only terms, always with year= (and month= when you know it from the
   by-year index).
2. If a search_titles call returns ZERO results, do NOT retry it with
   different patterns — switch immediately to grep_corpus (year=, month= if
   known). Do not call list_year or list_section.
3. Do NOT re-verify figures by grepping them ("315.04", "440.87", etc.) — the
   read_file output you already have is the source of truth. One read of the
   primary doc is enough; a second read is only for a genuinely missing detail.
   For long docs (400+ lines), read_file WITHOUT a line range returns a heading
   outline with line numbers — use that to jump straight to the section you
   need (e.g. "#### Transitorios"), then read_file with start_line/end_line.
   Do NOT ask for the whole doc at once; the outline is the map.
4. Skip *_AVISO_* files unless the question is about a notice/bid/edict.
5. Answer within 8 model turns total (locate ~3, verify ~2, answer ~1).
6. Anchor your search on the question's "as of" date and number of hops: if
   the question is about events that happened BY that date, search the most
   recent years/months first — do not wander into old years without evidence.
{meta}

Question: {question}
"""


def _est_tokens(messages: list[dict]) -> int:
    """Rough token estimate (Spanish ~3 chars/token; be conservative /3)."""
    total = 0
    for m in messages:
        c = m.get("content")
        if isinstance(c, str):
            total += max(1, len(c) // 3)
        elif isinstance(c, list):
            for part in c:
                if isinstance(part, dict):
                    total += len(str(part.get("text", ""))) // 3
        for tc in m.get("tool_calls") or []:
            # tc may be a pydantic object or a plain dict
            args = getattr(tc, "function", None)
            if isinstance(args, dict):
                total += len(args.get("arguments") or "") // 3
            elif args is not None:
                total += len(getattr(args, "arguments", "") or "") // 3
    return total


def compact_messages(messages: list[dict], findings: list[str]) -> list[dict]:
    """Drop the middle of the conversation, keep head + digest + current round.

    Head: system + the seeded user turn. Digest: a synthesized assistant
    summary of tool findings so far (relpaths, key numbers). Tail: the last
    assistant tool-call round and its results, so in-flight tool ids stay
    valid. Whole (assistant + tool) segments are dropped together — never a
    dangling tool result.
    """
    head = messages[:2]
    # index of the newest assistant message that issued tool_calls
    idx = None
    for i in range(len(messages) - 1, -1, -1):
        if messages[i].get("tool_calls"):
            idx = i
            break
    if idx is None or idx <= 1:
        return messages
    tail = messages[idx:]
    digest_body = "\n".join(findings[-25:]) if findings else "(ninguna búsqueda previa)"
    digest = (
        "Resumen de lo localizado y leído hasta ahora con herramientas "
        "(conserva esto; el detalle completo fue compactado):\n" + digest_body
    )
    # Merge the digest into the FIRST retained assistant message's content.
    # Do NOT insert a standalone assistant digest message: DeepSeek's
    # thinking-mode validation rejects an extra assistant turn immediately
    # before a tool-call turn ("reasoning_content must be passed back").
    first = tail[0]
    if first.get("role") == "assistant":
        first = {**first, "content": digest + "\n\n" + (first.get("content") or "")}
    else:
        tail = [{"role": "assistant", "content": digest}] + tail
    # keep the tail bounded (last ~8 messages) to cap growth between compactions
    tail = [first] + tail[1:]
    if len(tail) > 8:
        tail = tail[-8:]
    return head + tail


def run_question(
    client,
    model: str,
    question: str,
    qid: str = "",
    category: str = "",
    meta: str = "",
    *,
    max_tokens: int | None = None,
    workspace: Path | None = None,
    on_event=None,
) -> dict:
    """Run one question through the file-based agent loop.

    ``on_event`` is an optional callback receiving a plain dict for each
    observable step:

    - {"type": "model_turn_started", "turn": int, "cap": int}
    - {"type": "tool_started", "tool": str, "args": dict}
    - {"type": "tool_completed", "tool": str, "args": dict, "ok": bool,
       "content": str | None, "error": str | None}

    The CLI and the web executor use it to stream progress to the user. It is
    always called with JSON-serialisable values.
    """
    workspace = workspace or WORKSPACE
    # System carries the workspace context + the question. Some local servers
    # (LM Studio / Qwen jinja templates) require at least one user turn, so
    # always seed a brief user message referencing the system prompt.
    messages = [
        {"role": "system", "content": build_system_prompt(workspace, question, meta)},
        {"role": "user", "content": "Responde la pregunta del system prompt usando las herramientas disponibles. Sigue las reglas de eficiencia."},
    ]
    findings: list[str] = []
    trace: list[dict] = []
    usage = {"input_tokens": 0, "output_tokens": 0}
    cap = max_turns_for(qid, category)
    compact_threshold = int(CTX_WINDOW * CTX_COMPACT_AT)

    for _turn in range(cap):
        est = _est_tokens(messages)
        if est > compact_threshold:
            before = len(messages)
            messages = compact_messages(messages, findings)
            print(
                f"    [ctx] compacted: ~{est/1000:.1f}k tokens, "
                f"{before} -> {len(messages)} messages",
                flush=True,
            )
        print(f"    [turn {_turn}/{cap}] calling API (~{_est_tokens(messages)/1000:.1f}k tokens)...", flush=True)
        if on_event is not None:
            on_event(
                {
                    "type": "model_turn_started",
                    "turn": _turn,
                    "cap": cap,
                }
            )
        kwargs: dict = {
            "model": model,
            "messages": messages,
            "tools": tool_schemas(),
            "tool_choice": "auto",
            "timeout": 600,
        }
        # reasoning_effort is only understood by reasoning-capable backends
        # (DeepSeek, OpenAI reasoning, ...); local OpenAI-compatible servers
        # may ignore or reject it. Set DOF_REASONING_EFFORT="" to omit it.
        reasoning_effort = os.environ.get("DOF_REASONING_EFFORT", "minimal")
        if reasoning_effort:
            kwargs["reasoning_effort"] = reasoning_effort
        if max_tokens is not None:
            kwargs["max_tokens"] = max_tokens
        resp = client.chat.completions.create(**kwargs)
        msg = resp.choices[0].message
        print(
            f"    [turn {_turn}] finish={resp.choices[0].finish_reason} "
            f"calls={len(msg.tool_calls or [])} content_len={len(msg.content or '')}",
            flush=True,
        )
        if resp.usage:
            usage["input_tokens"] += resp.usage.prompt_tokens or 0
            usage["output_tokens"] += resp.usage.completion_tokens or 0
        if msg.tool_calls:
            asm: dict = {
                "role": "assistant",
                "content": msg.content or "",
                "tool_calls": msg.tool_calls,
            }
            # DeepSeek thinking mode: reasoning_content must be echoed back on
            # assistant tool-call turns (LM Studio/Qwen tolerate the extra key)
            rc = getattr(msg, "reasoning_content", None)
            if rc:
                asm["reasoning_content"] = rc
            messages.append(asm)
        else:
            messages.append({"role": "assistant", "content": msg.content or ""})
        if not msg.tool_calls:
            break
        for tc in msg.tool_calls:
            try:
                args = json.loads(tc.function.arguments or "{}")
            except json.JSONDecodeError:
                args = {}
            if on_event is not None:
                on_event({"type": "tool_started", "tool": tc.function.name, "args": args})
            result = call_tool(workspace, tc.function.name, args)
            trace.append(
                {"tool": tc.function.name, "args": args, "ok": result.get("ok", False)}
            )
            # record a compact finding for the compaction digest
            if result.get("ok"):
                cont = result.get("content", "")
                if tc.function.name in ("search_titles", "grep_corpus"):
                    rels = [m.get("relpath", "") for m in (json.loads(cont) if cont.startswith("[") else [])][:6]
                    findings.append(f"- {tc.function.name}({args.get('pattern','')[:60]}): {len(rels)} resultados: {', '.join(rels)}")
                elif tc.function.name == "read_file":
                    head = " ".join(cont.split())[:200]
                    findings.append(f"- read_file {args.get('relpath','')}: {head}...")
                else:
                    findings.append(f"- {tc.function.name}({str(args)[:100]}): ok")
            else:
                findings.append(f"- {tc.function.name}({str(args)[:80]}): fallo")
            if on_event is not None:
                on_event(
                    {
                        "type": "tool_completed",
                        "tool": tc.function.name,
                        "args": args,
                        "ok": result.get("ok", False),
                        "content": result.get("content") if result.get("ok") else None,
                        "error": result.get("error") if not result.get("ok") else None,
                    }
                )
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": json.dumps(result, ensure_ascii=False)[:TOOL_RESULT_CHARS],
                }
            )
    else:
        return {"id": qid, "error": "max_turns_exceeded", "trace": trace}

    return {
        "id": qid,
        "question": question,
        "answer": msg.content or "",
        "trace": trace,
        "usage": usage,
        "stop_reason": "completed" if msg.content else "empty",
    }
