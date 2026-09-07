# DOF-ICM — Portable, File-Based DOF Q&A

A portable, file-based workspace for answering questions about Mexican federal law using the *Diario Oficial de la Federación* (DOF) corpus (2024–2026). **No embeddings, no vector DB, no server.** The corpus is markdown files; retrieval is a skill the agent reads; answers are markdown with citations.

Built on the [Interpretable Context Methodology (ICM)](https://github.com/RinDig/Interpretable-Context-Methodology) — folder structure as agent architecture.

## What it is

- **A folder**, not a service. Drop it into any agent harness (Claude Code, Codex, DSH, Hermes, etc.) and it works.
- **The corpus is the state.** One markdown file per DOF legal document, organized by `YYYY/MM/DATE/SECTION/`.
- **Retrieval is a skill.** The agent reads a `SKILL.md` + `rules/*.md` to learn how to navigate and grep the corpus.
- **Answers are markdown.** Every factual claim cites a specific doc (relpath + line range + date + section).

## What it is not

- Not a RAG pipeline. No chunking, no embeddings, no vector index.
- Not a server. No HTTP, no API, no state to manage.
- Not a general legal assistant. It answers questions that the 2024–2026 DOF corpus can support. If the corpus doesn't contain the answer, it says so.

## Requirements

- **An agent harness** that can read markdown files and execute shell commands (grep, etc.)
- **A model** (recommended: DeepSeek `deepseek-v4-flash` via `https://api.deepseek.com/v1`, key in `DEEPSEEK_API_KEY`)
- **The corpus** (`corpus/` folder) — either committed to the repo or downloaded via the setup script

## Quickstart

### 1. Get the corpus

If `corpus/` is empty, run the one-shot builder (from the repo root). It downloads
the `.doc` files, converts them to markdown, and produces the same optimized
state as the reference build — HTML-junk cleanup, retries for large decrees,
verified delete of `.doc`, and navigation indexes:

```bash
# from the repo root (needs uv + LibreOffice + pandoc)
dof-icm/scripts/setup.sh                      # full 2024-2026 corpus (~hours)
dof-icm/scripts/setup.sh 01/01/2025 31/12/2025  # narrower range
```

Under the hood this runs `dof-icm/scripts/build_corpus.py`, which mirrors the
reference build pipeline exactly (see its header comment). The `.doc` sources
are deleted only after each `.md` is verified, and any unconvertible files are
kept under `dof-icm/dof_failed/` for inspection rather than silently lost.

> (The older manual path — `uv run get_word_dof.py …` then
> `convert_doc_to_md.py --input-dir ./dof_word --output-dir ./dof-icm/corpus`
> then `rm -rf dof_word/` — is still available but does NOT reproduce the
> reference quality: it deletes `.doc` files even when conversion failed.)

### 2. Configure your harness

Point your agent at the `dof-icm/` folder and use this model config:

```
provider: deepseek        # OpenAI-compatible API
endpoint: https://api.deepseek.com/v1
model: deepseek-v4-flash
api_key: $DEEPSEEK_API_KEY
```

### 3. Ask a question

```
User: ¿Cuál es el salario mínimo general diario vigente en 2026?

Agent (Stage 01 — locate):
  - Classifies: year=2026, section=MAT, terms="salario mínimo"
  - Reads corpus/index/by-year-2026.md
  - Greps corpus/2026/ for "salario mínimo"
  - Writes stages/01-locate/output/salario-minimo-2026-candidates.md

Agent (Stage 02 — verify):
  - Reads the candidate doc(s)
  - Extracts: $315.04, vigente desde 1 de enero de 2026
  - Writes stages/02-verify/output/salario-minimo-2026-answer.md

Agent (delivers):
  El salario mínimo general diario para 2026 es de $315.04 por jornada diaria,
  vigente desde el 1 de enero de 2026.
  [Acuerdo por el que se establecen los salarios mínimos 2026] (DOF, 2025-12-09, MAT)
  — 2025/12/09122025/MAT/006_DOF_20251209_MAT_5775533.md — lines 42–48
```

## Web UI (optional)

`web/` is a self-contained browser interface adapted from the upstream
dof-rag human-evaluation site (Air + Clerk, MIT). It keeps the full workflow —
auth, daily quota, review-before-ask, editorial publish queue, feedback, and a
live tool-progress timeline — but every question is answered by this same
file-based agent (`web/icm_executor.py` drives `scripts/icm_core.py`) over the
`corpus/` files, using **your own API key / subscription**. No embeddings, no
vector DB, no `dof_db`.

```bash
# from dof-icm/ (corpus/ + index already built; see Quickstart)
python -m venv web/.venv
web/.venv/bin/pip install -r web/requirements.txt
export DEEPSEEK_API_KEY=sk-...            # or DOF_AGENT_API_KEY / OPENAI_API_KEY
export DOF_LOCAL_PASSWORD='a-strong-password'   # local single-admin sign-in
web/.venv/bin/python -m web.app           # http://127.0.0.1:8765
```

See [`web/README.md`](web/README.md) for the full env reference (provider,
auth backends incl. Clerk, tuning knobs).

## Folder structure

```
dof-icm/
  CLAUDE.md                     # Layer 0: map, routing, model config
  CONTEXT.md                    # Layer 1: task routing
  corpus/                       # The DOF corpus (2024–2026)
    2024/01/02012024/MAT/...    # One .md per legal doc
    index/                      # Navigation maps (by-year, by-section, recent)
  stages/
    01-locate/                  # Find candidate docs
      CONTEXT.md
      references/
        citation-format.md
      output/                   # [slug]-candidates.md
    02-verify/                  # Extract + verify the answer
      CONTEXT.md
      references/
        answer-quality.md
      output/                   # [slug]-answer.md
  skills/
    dof-retrieval/
      SKILL.md                  # Retrieval skill (when to use + how)
      rules/
        navigate-year-section.md
        grep-patterns.md
        multi-doc-questions.md
        temporal-questions.md
  setup/
    questionnaire.md            # One-time onboarding
  eval/
    questions.jsonl             # Year-scoped eval set
    results/                    # Run outputs
  web/                          # Optional browser UI (human-eval workflow)
    app.py / icm_executor.py    # UI + file-backed executor
    requirements.txt / README.md
```

## The 5-layer routing

The agent reads *down* the layers and stops when it has enough context:

| Layer | File | Token cost | When loaded |
|-------|------|------------|-------------|
| 0 | `CLAUDE.md` | ~800 | Always (auto-loaded by harness) |
| 1 | `CONTEXT.md` | ~300 | On entry (task routing) |
| 2 | `stages/*/CONTEXT.md` | ~200–500 | Per-task (which stage) |
| 3 | `references/`, `skills/` | varies | Selectively (when needed) |
| 4 | `corpus/`, `output/` | varies | Per-run (the actual work) |

**No agent reads everything.** A locate agent reads Layers 0–2 + the skill. A verify agent reads Layers 0–2 + the candidates + the specific doc files.

## Eval

A year-scoped eval set (`eval/questions.jsonl`) constrained to 2024–2026 gold docs, using the 7-category taxonomy from the upstream `dof-rag` v4 set. Run results land in `eval/results/`.

## License

DOF content is public domain (Mexican government). Workspace code is MIT.
