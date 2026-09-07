"""File-backed executor powering the human-evaluation UI over DOF-ICM.

Drop-in replacement for the upstream ``human_eval/agent_executor.py`` (which
answers through ``agent_tools`` + the ``dof_db`` corpus/chunks/vec0 SQLite
stack). This executor answers the exact same ``RunRequest`` contract with the
DOF-ICM file-based agent (``scripts/icm_core``): it loads the ICM workspace
context, locates candidate documents with the title/body indexes, reads the
plain-markdown corpus files, and returns a result shaped like the upstream
public result so the UI (evidence, citations, documents, trace, provenance,
progress timeline) works unchanged.

No embeddings, no vector DB, no ``dof_db``. The only external dependency is an
OpenAI-compatible chat-completions endpoint, configured through the operator's
own API key / subscription (see ``IcmExecutorConfig.from_env``).
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:  # pragma: no cover - import guard parity with upstream
    from openai import OpenAI
except ImportError:  # pragma: no cover
    OpenAI = None

from .contracts import RunRequest
from .service import PublicExecutionError

# Make the workspace's scripts/ importable as a namespace package regardless
# of the current working directory (dof-icm/scripts has no __init__.py).
_WORKSPACE = Path(__file__).resolve().parent.parent
if str(_WORKSPACE) not in sys.path:
    sys.path.insert(0, str(_WORKSPACE))

from scripts import icm_core  # noqa: E402

DEFAULT_MODEL = "deepseek-v4-flash"
DEFAULT_BASE_URL = "https://api.deepseek.com/v1"

# Relpath pattern used to locate citations in the model's answer text:
# YYYY/MM/DDDATE/SECTION/<id>_DOF_YYYYMMDD_SECTION_<n>.md
RELPATH_RE = re.compile(
    r"20\d{2}/\d{2}/\d{8}/(?:MAT|VES)/[0-9A-Za-z_.\-]+\.md"
)

_OPENAI_ERROR_NAMES = frozenset(
    {
        "APIConnectionError",
        "APITimeoutError",
        "APIStatusError",
        "AuthenticationError",
        "BadRequestError",
        "InternalServerError",
        "NotFoundError",
        "PermissionDeniedError",
        "RateLimitError",
    }
)

_LOCAL_HOSTS = frozenset({"127.0.0.1", "localhost", "::1"})


def _endpoint_is_local(base_url: str) -> bool:
    from urllib.parse import urlparse

    try:
        return urlparse(base_url).hostname in _LOCAL_HOSTS
    except ValueError:
        return False


@dataclass(frozen=True)
class IcmExecutorConfig:
    workspace_root: Path
    model: str
    base_url: str
    api_key: str
    max_tokens: int | None = None
    retrieval_mode: str = "icm-files"

    @classmethod
    def from_env(cls, workspace_root: str | Path) -> "IcmExecutorConfig":
        root = Path(workspace_root).resolve()
        base_url = os.environ.get("DOF_AGENT_BASE_URL") or DEFAULT_BASE_URL
        api_key = (
            os.environ.get("DOF_AGENT_API_KEY")
            or os.environ.get("DEEPSEEK_API_KEY")
            or os.environ.get("OPENAI_API_KEY")
            or os.environ.get("KIMI_API_KEY")
            or ""
        )
        if not api_key and _endpoint_is_local(base_url):
            # Local OpenAI-compatible servers (llama.cpp llama-server, LM
            # Studio, vLLM, ...) ignore the key; the placeholder satisfies the
            # OpenAI client.
            api_key = "local"
        model = os.environ.get("DOF_AGENT_MODEL") or DEFAULT_MODEL
        raw_max = os.environ.get("DOF_ICM_MAX_TOKENS") or os.environ.get(
            "DOF_MAX_TOKENS"
        )
        max_tokens = int(raw_max) if raw_max else None
        if not (root / "corpus").is_dir():
            raise ValueError(
                f"no corpus/ directory under workspace {root}; "
                "build it first (dof-icm/scripts/setup.sh)"
            )
        return cls(
            workspace_root=root,
            model=model,
            base_url=base_url,
            api_key=api_key,
            max_tokens=max_tokens,
        )


def _relpath_meta(relpath: str) -> dict[str, str | None]:
    """Derive date/section/stable id from a corpus relpath."""
    parts = relpath.split("/")
    if len(parts) < 5 or len(parts[0]) != 4 or len(parts[2]) != 8:
        return {}
    year, month, day = parts[0], parts[1], parts[2][0:2]
    date = f"{year}-{month}-{day}"
    return {
        "publication_date": date,
        "section": parts[3],
        "document_id_hint": parts[4],
    }


class _TitleIndex:
    """Lazy relpath → title lookup over corpus/index/titles-YYYY.md."""

    def __init__(self, index_root: Path):
        self.index_root = index_root
        self._cache: dict[str, dict[str, str]] = {}
        self._lock = threading.Lock()

    def title_for(self, relpath: str) -> str | None:
        year = relpath[0:4]
        if not year.isdigit():
            return None
        with self._lock:
            table = self._cache.get(year)
            if table is None:
                table = {}
                path = self.index_root / f"titles-{year}.md"
                if path.exists():
                    try:
                        for line in path.read_text(encoding="utf-8").splitlines():
                            rel, _, title = line.partition("\t")
                            if rel and title:
                                table.setdefault(rel.strip(), title.strip())
                    except OSError:
                        table = {}
                self._cache[year] = table
            return table.get(relpath)


class IcmRunExecutor:
    """Run the ICM file-based agent, sharing nothing across runs.

    Each run is a self-contained conversation against the OpenAI-compatible
    endpoint; tool results are streamed to the UI through ``on_progress``.
    """

    def __init__(self, config: IcmExecutorConfig):
        self.config = config
        self.corpus = config.workspace_root / "corpus"
        self.index = self.corpus / "index"
        self.titles = _TitleIndex(self.index)

    # -- lifecycle (called by EvaluationService) ---------------------------

    def prepare(self) -> None:
        """Fail fast when the file corpus is unusable before a run is queued."""
        if not (self.corpus / "2024").is_dir():
            raise PublicExecutionError(
                "provider_unavailable",
                "El corpus de archivos no está disponible.",
            )
        if not (self.index / "titles-2024.md").exists():
            raise PublicExecutionError(
                "provider_unavailable",
                "El índice del corpus no está disponible.",
            )

    def close(self) -> None:
        pass

    def provenance(self) -> dict[str, Any]:
        revision, dirty = _git_snapshot(self.config.workspace_root)
        years: list[str] = []
        corpus_documents: int | None = None
        for path in sorted(self.index.glob("by-year-*.md")):
            years.append(path.stem.removeprefix("by-year-"))
        try:
            total = 0
            for path in self.index.glob("by-year-*.md"):
                text = path.read_text(encoding="utf-8", errors="replace")
                match = re.search(r"total\s*[:\-]?\s*([\d,]+)", text, re.IGNORECASE)
                if match:
                    total += int(match.group(1).replace(",", ""))
            corpus_documents = total or None
        except OSError:
            corpus_documents = None
        return {
            "code_revision": revision,
            "code_dirty": dirty,
            "corpus_mode": "icm-files",
            "corpus_documents": corpus_documents,
            "corpus_years": years,
            "vector_available": False,
            "vector_used": False,
            "provider": "openai-compatible",
            "model": self.config.model,
            "configuration": {
                "retrieval_mode": self.config.retrieval_mode,
                "base_url": _redact(self.config.base_url),
                "max_tokens": self.config.max_tokens,
            },
        }

    # -- the run -----------------------------------------------------------

    def execute(
        self,
        request: RunRequest,
        *,
        on_progress=None,
    ) -> dict[str, Any]:
        started = time.monotonic()
        if OpenAI is None:
            raise PublicExecutionError(
                "provider_unavailable",
                "El paquete openai no está instalado.",
            )
        if not self.config.api_key:
            raise PublicExecutionError(
                "provider_unavailable",
                "El proveedor del agente no está configurado.",
            )

        # Question metadata the agent uses to anchor its search in time and
        # to know how many source documents to read.
        bits = []
        if request.as_of:
            bits.append(f'Reference date ("as of"): {request.as_of}')
        if request.required_hops:
            bits.append(f"Required hops (documents): {request.required_hops}")
        meta = ("\n".join(f"6b. {b}" for b in bits)) if bits else ""

        client = OpenAI(api_key=self.config.api_key, base_url=self.config.base_url)
        state = _RunState(self, request)

        if on_progress is not None:
            on_progress(
                "agent_started",
                {
                    "message": (
                        "El agente cargó el contexto del workspace y comienza "
                        "la búsqueda en el corpus."
                    ),
                },
            )

        def _translate(event: dict[str, Any]) -> None:
            if on_progress is None:
                return
            kind = event["type"]
            if kind == "model_turn_started":
                state.record_model_turn()
                turn, cap = event["turn"], event["cap"]
                on_progress(
                    "model_turn_started",
                    {
                        "message": (
                            f"Turno {turn + 1}/{cap}: el modelo analiza lo "
                            "encontrado y decide su siguiente acción."
                        ),
                        "why": "Decisión observable del modelo; el razonamiento interno no se publica.",
                    },
                )
            elif kind == "tool_started":
                label = icm_core._tool_label(event["tool"], event["args"])
                on_progress(
                    "tool_started",
                    {
                        "message": label,
                        "why": _TOOL_WHY.get(event["tool"], ""),
                    },
                )
            elif kind == "tool_completed":
                payload = state.record_tool_completed(
                    event["tool"], event["args"], event["ok"],
                    event.get("content"), event.get("error"),
                )
                if on_progress is not None and payload is not None:
                    on_progress("tool_completed", payload)

        try:
            run = icm_core.run_question(
                client,
                self.config.model,
                request.question,
                qid="",
                meta=meta,
                max_tokens=self.config.max_tokens,
                workspace=self.config.workspace_root,
                on_event=_translate,
            )
        except PublicExecutionError:
            raise
        except Exception as exc:
            name = type(exc).__name__
            status_code = getattr(exc, "status_code", None)
            if name in _OPENAI_ERROR_NAMES:
                code = (
                    "rate_limited"
                    if name == "RateLimitError" or status_code == 429
                    else "provider_unavailable"
                )
                raise PublicExecutionError(
                    code, "El proveedor del agente no está disponible."
                ) from exc
            raise

        if run.get("error"):
            code = run["error"]
            message = (
                "El agente agotó su presupuesto de turnos sin terminar la "
                "respuesta."
                if code == "max_turns_exceeded"
                else "La ejecución del agente no pudo completarse."
            )
            raise PublicExecutionError(code, message)

        answer = run.get("answer") or ""
        if not answer.strip():
            raise PublicExecutionError(
                "empty_answer",
                "El agente no produjo una respuesta de texto.",
            )

        result = state.build_result(
            answer=answer,
            usage=run.get("usage", {}),
            elapsed_ms=int((time.monotonic() - started) * 1000),
            stop_reason=run.get("stop_reason", "completed"),
            model_turns=state.model_turns,
            tool_calls=state.tool_calls,
            trace=run.get("trace", []),
        )
        return result


_TOOL_WHY = {
    "search_titles": (
        "Localiza candidatos por título/institucion antes de leer documentos."
    ),
    "grep_corpus": (
        "El índice de títulos no bastó; busca el término en el cuerpo del corpus."
    ),
    "read_file": "Extrae el pasaje exacto que sustentará la cita.",
    "list_year": "Revisa qué documentos y meses cubre el corpus ese año.",
    "list_section": "Revisa la cobertura de la sección MAT o VES.",
}


class _RunState:
    """Accumulates tool activity + doc/chunk registries for one run."""

    def __init__(self, executor: "IcmRunExecutor", request: RunRequest):
        self.executor = executor
        self.request = request
        self.model_turns = 0
        self.tool_calls = 0
        # relpath -> document_id (assigned in order of first appearance)
        self._doc_ids: dict[str, int] = {}
        self._documents: dict[int, dict[str, Any]] = {}
        self._chunks: list[dict[str, Any]] = []
        self._next_doc_id = 1
        self._next_chunk_id = 1

    # -- registry helpers ---------------------------------------------------

    def _doc_id_for(self, relpath: str) -> int:
        doc_id = self._doc_ids.get(relpath)
        if doc_id is not None:
            return doc_id
        doc_id = self._next_doc_id
        self._next_doc_id += 1
        self._doc_ids[relpath] = doc_id
        meta = _relpath_meta(relpath)
        title = self.executor.titles.title_for(relpath)
        self._documents[doc_id] = {
            "document_id": doc_id,
            "path": relpath,
            "publication_date": meta.get("publication_date"),
            "section": meta.get("section"),
            "title": title or meta.get("document_id_hint"),
            "institution": None,
            "used_as_evidence": False,
            "cited": False,
        }
        return doc_id

    def _document_item(self, relpath: str) -> dict[str, Any]:
        return dict(self._documents[self._doc_id_for(relpath)])

    def record_model_turn(self) -> None:
        self.model_turns += 1

    def record_tool_completed(
        self,
        tool: str,
        args: dict[str, Any],
        ok: bool,
        content: str | None,
        error: str | None,
    ) -> dict[str, Any] | None:
        self.tool_calls += 1
        if tool == "read_file" and ok and content:
            relpath = str(args.get("relpath", ""))
            if relpath:
                doc_id = self._doc_id_for(relpath)
                doc = self._documents[doc_id]
                doc["used_as_evidence"] = True
                excerpt = _read_excerpt(args, content)
                chunk = {
                    "chunk_id": self._next_chunk_id,
                    "document_id": doc_id,
                    "path": relpath,
                    "text": excerpt[:4000],
                    "cited": False,
                }
                self._next_chunk_id += 1
                self._chunks.append(chunk)
                message = (
                    f"Leído: {relpath} ({_count_lines(content)} líneas devueltas)"
                )
                if args.get("start_line") or args.get("end_line"):
                    message = (
                        f"Leído: {relpath} (líneas "
                        f"{args.get('start_line', 1)}–{args.get('end_line', 'fin')})"
                    )
                return {
                    "message": message,
                    "why": "",
                    "documents": [_chip(doc)],
                    "chunks": [_chunk_payload(chunk)],
                }
        if tool in ("search_titles", "grep_corpus") and ok and content:
            items = _parse_items(content)
            if items:
                docs = []
                for item in items:
                    relpath = item.get("relpath", "")
                    if not relpath:
                        continue
                    doc = self._documents[self._doc_id_for(relpath)]
                    if item.get("title"):
                        doc["title"] = item["title"]
                    docs.append(_chip(doc))
                message = (
                    f"{len(items)} {'documento' if len(items) == 1 else 'documentos'} "
                    f"localizados"
                )
                return {"message": message, "why": "", "documents": docs}
        if tool in ("search_titles", "grep_corpus") and ok:
            return {"message": "Sin resultados en esa búsqueda.", "why": ""}
        if not ok:
            rel = str(args.get("relpath", ""))
            detail = (error or "").strip()
            if rel:
                return {
                    "message": f"No se pudo leer {rel}"
                    + (f": {detail}" if detail else ""),
                    "why": "",
                }
            return {
                "message": "La búsqueda no pudo completarse" + (f": {detail}" if detail else ""),
                "why": "",
            }
        return None

    # -- final mapping -------------------------------------------------------

    def build_result(
        self,
        *,
        answer: str,
        usage: dict[str, int],
        elapsed_ms: int,
        stop_reason: str,
        model_turns: int,
        tool_calls: int,
        trace: list[dict[str, Any]],
    ) -> dict[str, Any]:
        cited = _cited_relpaths(answer)
        # Mark documents cited (model cited the doc relpath in the answer).
        for relpath in cited:
            if relpath in self._doc_ids:
                self._documents[self._doc_ids[relpath]]["cited"] = True
        # Mark evidence chunks of cited docs, and their citation ids.
        citation_ids: list[int] = []
        for chunk in self._chunks:
            doc = self._documents[chunk["document_id"]]
            if doc["cited"]:
                chunk["cited"] = True
                citation_ids.append(chunk["chunk_id"])
        citation_ids.sort()

        required_hops = max(1, int(self.request.required_hops or 1))
        read_count = sum(
            1 for doc in self._documents.values() if doc["used_as_evidence"]
        )
        coverage_complete = read_count >= required_hops and stop_reason == "completed"
        coverage = {
            "required": [f"documento_{i + 1}" for i in range(required_hops)],
            "missing": (
                [f"documento_{i + 1}" for i in range(read_count, required_hops)]
                if read_count < required_hops
                else []
            ),
            "complete": coverage_complete,
        }
        warnings: list[str] = []
        if not coverage_complete:
            warnings.append("coverage_incomplete")
        return {
            "answer": {
                "text": answer,
                "citation_ids": citation_ids,
                "premise_status": "unknown",
            },
            "evidence": sorted(
                self._chunks, key=lambda item: item["chunk_id"]
            ),
            "documents": sorted(
                self._documents.values(), key=lambda item: item["document_id"]
            ),
            "coverage": coverage,
            "verification": {},
            "trace": trace,
            "warnings": warnings,
            "stop_reason": stop_reason,
            "model_turns": model_turns,
            "tool_calls": tool_calls,
            "usage": usage,
            "elapsed_ms": elapsed_ms,
        }


def _git_snapshot(workspace: Path) -> tuple[str, bool]:
    """Best-effort git revision of the workspace (repo or standalone copy)."""
    try:
        revision = subprocess.run(
            ["git", "-C", str(workspace), "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        dirty = bool(
            subprocess.run(
                ["git", "-C", str(workspace), "status", "--porcelain",
                 "--untracked-files=all"],
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip()
        )
    except (OSError, subprocess.CalledProcessError):
        return "unknown", True
    return revision, dirty


def _redact(base_url: str) -> str:
    try:
        from urllib.parse import urlparse

        parsed = urlparse(base_url)
        if parsed.password:
            return base_url.replace(parsed.password, "***")
    except ValueError:
        pass
    return base_url


def _chip(document: dict[str, Any]) -> dict[str, Any]:
    return {
        "document_id": document["document_id"],
        "path": document["path"],
        "publication_date": document.get("publication_date"),
        "title": document.get("title"),
    }


def _chunk_payload(chunk: dict[str, Any]) -> dict[str, Any]:
    return {
        "chunk_id": chunk["chunk_id"],
        "document_id": chunk["document_id"],
        "path": chunk["path"],
        "excerpt": chunk["text"],
    }


def _parse_items(content: str) -> list[dict[str, Any]]:
    stripped = content.strip()
    if stripped.startswith("["):
        try:
            items = json.loads(stripped)
            if isinstance(items, list):
                return [i for i in items if isinstance(i, dict)]
        except (json.JSONDecodeError, TypeError):
            pass
    return []


def _count_lines(content: str) -> int:
    return len(content.splitlines())


def _read_excerpt(args: dict[str, Any], content: str) -> str:
    """Extract the readable passage from a read_file tool result.

    Long-document reads without a line range return a heading outline plus the
    first 200 lines after a marker; only the actual body is shown as evidence.
    """
    lines = content.splitlines()
    if lines and lines[0].startswith("# "):
        lines = lines[1:]
    text = "\n".join(lines)
    if not (args.get("start_line") or args.get("end_line")):
        marker = "--- first 200 lines ---"
        if marker in text:
            text = text.split(marker, 1)[1]
    return text.strip()


def _cited_relpaths(answer: str) -> set[str]:
    """Relpaths the model cited in its answer (``citation-format.md``)."""
    found = set(RELPATH_RE.findall(answer))
    # Heuristic: strip trailing punctuation gluing to the citation marker.
    return {rel.strip().rstrip(".,;") for rel in found if rel.strip()}
