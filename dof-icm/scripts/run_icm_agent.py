#!/usr/bin/env python3
"""Run the DOF-ICM two-stage agent against an OpenAI-compatible API.

The agent reads the ICM workspace context (CLAUDE.md, CONTEXT.md, stage
contracts, skill files) and answers a question using file-based tools
(grep_corpus, read_file, list_year, list_section) over the plain-markdown
corpus. No embeddings, no DB, no server.

Usage:
    DEEPSEEK_API_KEY=... python scripts/run_icm_agent.py \
        --question "¿Cuál es el salario mínimo general para 2026?"
    python scripts/run_icm_agent.py --eval-json eval/questions.jsonl --ids SP-001
    python scripts/run_icm_agent.py --eval-json eval/questions.jsonl --all
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

try:
    from openai import OpenAI
except ImportError:  # pragma: no cover
    OpenAI = None

WORKSPACE = Path(__file__).resolve().parent.parent
CORPUS = WORKSPACE / "corpus"
INDEX = CORPUS / "index"

# Stage-01 contract + skill are loaded as context; stage-02 follows.
LAYER0 = WORKSPACE / "CLAUDE.md"
LAYER1 = WORKSPACE / "CONTEXT.md"
STAGE1 = WORKSPACE / "stages/01-locate/CONTEXT.md"
STAGE1_REF = WORKSPACE / "stages/01-locate/references/citation-format.md"
STAGE2 = WORKSPACE / "stages/02-verify/CONTEXT.md"
STAGE2_REF = WORKSPACE / "stages/02-verify/references/answer-quality.md"
SKILL = WORKSPACE / "skills/dof-retrieval/SKILL.md"

MAX_TURNS = 6


def load_text(path: Path, limit: int = 12_000) -> str:
    if not path.exists():
        return f"[missing: {path}]"
    return path.read_text(encoding="utf-8")[:limit]


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


def call_tool(name: str, args: dict) -> dict:
    if name == "list_year":
        p = INDEX / f"by-year-{args['year']}.md"
        return {"ok": True, "content": load_text(p)}
    if name == "list_section":
        p = INDEX / f"by-section-{args['section']}.md"
        return {"ok": True, "content": load_text(p)}
    if name == "search_titles":
        year = args.get("year")
        if year:
            paths = [INDEX / f"titles-{year}.md"]
        else:
            paths = sorted(INDEX.glob("titles-*.md"))
        pattern = args["pattern"]
        max_res = int(args.get("max_results", 10))
        out = []
        for p in paths:
            if not p.exists():
                continue
            try:
                proc = subprocess.run(
                    ["grep", "-im1", "-E", pattern, str(p)],
                    capture_output=True, text=True, timeout=30,
                )
            except subprocess.TimeoutExpired:
                continue
            for line in proc.stdout.splitlines():
                if not line.strip():
                    continue
                rel, _, title = line.partition("\t")
                out.append({"relpath": rel, "title": title.strip()[:120]})
                if len(out) >= max_res:
                    break
            if len(out) >= max_res:
                break
        return {"ok": True, "content": json.dumps(out, ensure_ascii=False)}
    if name == "grep_corpus":
        base = CORPUS
        if args.get("year"):
            base = base / str(args["year"])
        if args.get("month"):
            base = base / args["month"]
        if args.get("section"):
            base = base / args["section"]
        if not base.exists():
            return {"ok": False, "error": f"path not found: {base.relative_to(CORPUS)}"}
        pattern = args["pattern"]
        max_res = int(args.get("max_results", 10))
        try:
            proc = subprocess.run(
                ["grep", "-rilE", "--include=*.md", pattern, str(base)],
                capture_output=True, text=True, timeout=60,
            )
            files = [l for l in proc.stdout.splitlines() if l.strip()][:max_res]
            out = []
            for f in files:
                fp = Path(f)
                rel = fp.relative_to(CORPUS).as_posix()
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
        p = CORPUS / rel
        if not p.exists():
            return {"ok": False, "error": f"not found: {rel}"}
        text = p.read_text(encoding="utf-8", errors="replace")
        lines = text.splitlines()
        # Default: return the WHOLE file (most docs are 100-600 lines) so the
        # agent doesn't burn turns re-reading chunks.
        start = int(args.get("start_line", 1)) - 1
        end = int(args.get("end_line", len(lines)))
        if end > len(lines):
            end = len(lines)
        chunk = "\n".join(lines[start:end])
        return {
            "ok": True,
            "content": f"# {rel} (lines {start+1}-{end}, total {len(lines)})\n" + chunk,
        }
    return {"ok": False, "error": f"unknown tool {name}"}


def build_system_prompt(question: str) -> str:
    return f"""{load_text(LAYER0)}

{load_text(LAYER1)}

--- STAGE 01 CONTRACT (run this first) ---
{load_text(STAGE1)}

Retrieval skill:
{load_text(SKILL)}

Citation format:
{load_text(STAGE1_REF)}

--- STAGE 02 CONTRACT (run after stage 01) ---
{load_text(STAGE2)}

Answer quality:
{load_text(STAGE2_REF)}

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
2. Do NOT call list_year "for context" — read it once only if you need month
   counts, then move on. Do not call list_section.
3. Do NOT re-verify figures by grepping them ("315.04", "440.87", etc.) — the
   read_file output you already have is the source of truth. One read of the
   primary doc is enough; a second read is only for a genuinely missing detail.
4. Skip *_AVISO_* files unless the question is about a notice/bid/edict.
5. Answer within 6 model turns total (locate ~2, verify ~1, answer ~1).

Question: {question}
"""


def run_question(client, model: str, question: str, qid: str = "") -> dict:
    messages = [{"role": "system", "content": build_system_prompt(question)}]
    trace: list[dict] = []
    usage = {"input_tokens": 0, "output_tokens": 0}

    for _turn in range(MAX_TURNS):
        print(f"    [turn {_turn}] calling API...", flush=True)
        resp = client.chat.completions.create(
            model=model,
            messages=messages,
            tools=tool_schemas(),
            tool_choice="auto",
            reasoning_effort="minimal",
            timeout=120,
        )
        msg = resp.choices[0].message
        print(
            f"    [turn {_turn}] finish={resp.choices[0].finish_reason} "
            f"calls={len(msg.tool_calls or [])} content_len={len(msg.content or '')}",
            flush=True,
        )
        if resp.usage:
            usage["input_tokens"] += resp.usage.prompt_tokens or 0
            usage["output_tokens"] += resp.usage.completion_tokens or 0
        messages.append(
            {"role": "assistant", "content": msg.content or "", "tool_calls": msg.tool_calls}
            if msg.tool_calls
            else {"role": "assistant", "content": msg.content or ""}
        )
        if not msg.tool_calls:
            break
        for tc in msg.tool_calls:
            try:
                args = json.loads(tc.function.arguments or "{}")
            except json.JSONDecodeError:
                args = {}
            result = call_tool(tc.function.name, args)
            trace.append(
                {"tool": tc.function.name, "args": args, "ok": result.get("ok", False)}
            )
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": json.dumps(result, ensure_ascii=False)[:8000],
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


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--question", help="Single question to answer")
    ap.add_argument("--eval-json", help="Path to eval/questions.jsonl")
    ap.add_argument("--ids", help="Comma-separated question ids (subset)")
    ap.add_argument("--all", action="store_true", help="All questions in eval set")
    ap.add_argument("--model", default="deepseek-v4-flash")
    ap.add_argument("--base-url", default="https://api.deepseek.com/v1")
    ap.add_argument("--out", default=str(WORKSPACE / "eval/results/run.jsonl"))
    args = ap.parse_args()

    api_key = os.environ.get("DEEPSEEK_API_KEY") or os.environ.get("OPENAI_API_KEY")
    if not api_key:
        sys.exit("set DEEPSEEK_API_KEY (or OPENAI_API_KEY)")
    if OpenAI is None:
        sys.exit("openai package not installed (uv sync)")

    client = OpenAI(api_key=api_key, base_url=args.base_url)
    questions: list[dict] = []
    if args.question:
        questions = [{"id": "manual", "question": args.question}]
    elif args.eval_json:
        with open(args.eval_json) as f:
            questions = [json.loads(l) for l in f if l.strip()]
        if args.ids:
            ids = {i.strip() for i in args.ids.split(",")}
            questions = [q for q in questions if q["id"] in ids]
        elif not args.all:
            by_cat: dict[str, dict] = {}
            for q in questions:
                by_cat.setdefault(q["category"], q)
            questions = list(by_cat.values())  # one per category (7)
    else:
        sys.exit("provide --question or --eval-json")

    results = []
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    for q in questions:
        print(f"==> {q['id']}: {q['question'][:80]}", flush=True)
        r = run_question(client, args.model, q["question"], q["id"])
        results.append(r)
        with open(out_path, "a") as f:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
        print(f"    stop={r.get('stop_reason')} tools={len(r.get('trace', []))}", flush=True)
        if r.get("answer"):
            print(f"    answer: {r['answer'][:200].replace(chr(10), ' ')}", flush=True)

    print(f"\nWrote {len(results)} results to {out_path}")


if __name__ == "__main__":
    main()
