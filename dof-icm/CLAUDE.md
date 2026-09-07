# DOF-ICM Workspace

Portable, file-based Q&A over the Mexican **Diario Oficial de la Federación** (DOF), 2024–2026. No embeddings, no vector DB, no server (the optional `web/` browser UI still uses the same file-based agent). The corpus is markdown files; retrieval is a skill the agent reads; answers are markdown with citations.

## Model

- **Provider:** DeepSeek API (OpenAI-compatible)
- **Endpoint:** `https://api.deepseek.com/v1`
- **Model:** `deepseek-v4-flash`
- **API key:** `DEEPSEEK_API_KEY` environment variable (set by the operator; never commit it)
- The agent (any harness) must be configured to use this model. The workspace itself is model-agnostic — it only prescribes the context the agent should read.

## Folder map

| Path | Role |
|---|---|
| `CLAUDE.md` | This file — Layer 0, always loaded |
| `CONTEXT.md` | Layer 1 — task routing |
| `corpus/` | Layer 4 — the DOF markdown corpus (2024–2026), one file per legal document |
| `corpus/index/` | Navigation maps (by-year, by-section, recent, titles) |
| `stages/01-locate/` | Stage 1 — find candidate docs for a question |
| `stages/02-verify/` | Stage 2 — read candidates, extract + verify the answer |
| `skills/dof-retrieval/` | Bundled retrieval knowledge (SKILL.md + rules/) |
| `setup/` | One-time onboarding (optional) |
| `eval/` | Year-scoped eval set + run results |
| `web/` | Optional browser UI — human-eval workflow over the file agent (`web/README.md`) |

## Routing table

| Task | Start here |
|---|---|
| "Answer a question about Mexican law / DOF" | `stages/01-locate/CONTEXT.md` |
| "Audit / improve a previous answer" | `stages/02-verify/CONTEXT.md` |
| "Set up the workspace" | `setup/questionnaire.md` |
| "Run the browser UI / human-eval site" | `web/README.md` |
| "How do I use this in my harness?" | `README.md` |

## Conventions

- **Citations** must use the format in `stages/01-locate/references/citation-format.md`.
- **One stage, one job.** Stage 01 locates; stage 02 verifies. Never mix.
- **Plain text only.** Every artifact is markdown. The filesystem is the state.
- **Load only what you need.** Read `CONTEXT.md` → stage `CONTEXT.md` → specific reference files. Do not read the whole corpus.
