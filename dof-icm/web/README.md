# DOF-ICM Web UI

A self-contained web interface for the DOF-ICM workspace — a file-backed
version of the upstream [dof-rag human-evaluation site](https://github.com/CodeandoGuadalajara/dof-rag)
(`human_eval/`, Air + Clerk, MIT). It keeps the whole human-evaluation
workflow (auth, daily quota, review-before-ask, publish queue, feedback,
live progress timeline) but answers every question with the **DOF-ICM
file-based agent**: no embeddings, no vector DB, no `dof_db`, no GGUF model.

Questions are answered by reading the plain-markdown corpus with the same
agent loop as `scripts/run_icm_agent.py` (see `scripts/icm_core.py`), using
**your own API key / subscription** to any OpenAI-compatible endpoint
(DeepSeek by default).

## Layout

| Path | Role |
|---|---|
| `web/app.py` | Air application, adapted from upstream `human_eval/app.py` |
| `web/icm_executor.py` | File-backed executor replacing `agent_executor.py` |
| `web/store.py`, `web/service.py` | Run queue + SQLite persistence (upstream, verbatim) |
| `web/contracts.py`, `web/markdown_render.py` | Upstream, verbatim |
| `web/auth.py` | Auth seam + local single-admin backend |
| `web/clerk_auth.py` | Clerk backend (upstream); only used with Clerk |
| `var/human_evaluation.sqlite` | Run/eval database (created at runtime, not committed) |

The web UI is self-contained inside `web/`: nothing outside `dof-icm/` is
imported. Data lives in `web/var/` (gitignored).

## Quickstart

Prerequisites: the corpus (`../corpus/`, built with `../scripts/setup.sh`),
Python 3.13+, and an API key.

```bash
# from the dof-icm/ workspace root
python -m venv web/.venv
web/.venv/bin/pip install -r web/requirements.txt

# your model subscription (DeepSeek default; or any OpenAI-compatible endpoint)
export DEEPSEEK_API_KEY=sk-...            # or DOF_AGENT_API_KEY / OPENAI_API_KEY
# export DOF_AGENT_BASE_URL=https://api.deepseek.com/v1
# export DOF_AGENT_MODEL=deepseek-v4-flash

# local single-admin sign-in (needed to ask questions / publish)
export DOF_LOCAL_PASSWORD='choose-a-strong-password'
# export DOF_SESSION_SECRET=$(python -c "import secrets; print(secrets.token_urlsafe(48))")

web/.venv/bin/python -m web.app          # http://127.0.0.1:8765
```

If you cloned the fork and already created the legacy python env
(`cd dof-rag && uv sync`), you can run the UI with that interpreter too
(from `dof-icm/`): `../dof-rag/.venv/bin/python -m web.app`.

Open http://127.0.0.1:8765 → Entrar → password → ask a question. Watch the
live tool timeline, then inspect the cited answer, the documents consulted and
the passages read. As the single local admin you can also publish answers so
anonymous visitors can read them.

## Configuration

Model (bring your own key):

| Env var | Default | Meaning |
|---|---|---|
| `DEEPSEEK_API_KEY` / `DOF_AGENT_API_KEY` / `OPENAI_API_KEY` / `KIMI_API_KEY` | — | API key (first one found wins) |
| `DOF_AGENT_BASE_URL` | `https://api.deepseek.com/v1` | OpenAI-compatible endpoint |
| `DOF_AGENT_MODEL` | `deepseek-v4-flash` | Model id on that endpoint |
| `DOF_ICM_MAX_TOKENS` | unset | `max_tokens` per completion (some local servers require it) |
| `DOF_REASONING_EFFORT` | `minimal` | Set `""` for servers that reject the parameter |
| `DOF_MAX_TURNS` | 8 (category-aware) | Tool-loop budget per question |
| `DOF_CTX_WINDOW_TOKENS`, `DOF_CTX_COMPACT_AT`, `DOF_TOOL_RESULT_CHARS` | 56000 / 0.60 / 24000 | Context compaction (see `scripts/icm_core.py`) |

Auth:

| Env var | Default | Meaning |
|---|---|---|
| `DOF_AUTH_BACKEND` | `auto` | `auto` → Clerk if `CLERK_SECRET_KEY` is set, else `local`. Explicit: `clerk`, `local`, `header`. |
| `DOF_LOCAL_PASSWORD` | — | Local admin password. Unset → sign-in page explains; site is read-only. |
| `DOF_LOCAL_EMAIL` | `admin@local` | Local admin identity shown in the UI |
| `CLERK_SECRET_KEY` (+ other `CLERK_*`) | — | Multi-user Clerk auth (see upstream docs) |

Web/behaviour (all optional):

| Env var | Default | Meaning |
|---|---|---|
| `DOF_WEB_HOST` / `DOF_WEB_PORT` | `127.0.0.1` / `8765` | Bind address |
| `DOF_SESSION_SECRET` | ephemeral | ≥32 chars; fixed value keeps sessions across restarts |
| `DOF_ALLOWED_HOSTS` | `127.0.0.1,localhost` | Host header allowlist |
| `DOF_SECURE_COOKIE` | `false` | `true` behind HTTPS |
| `DOF_DAILY_QUESTION_LIMIT` | `1` | Questions per rolling 24h (admins exempt); `0` disables |
| `DOF_QUEUE_CAPACITY` | `20` | Local execution queue |
| `DOF_HUMAN_EVAL_DB` | `<workspace>/var/human_evaluation.sqlite` | Evaluation database |

## Notes

- **Auth model.** The full workflow needs an authenticated *user* to ask, a
  *review* before each question, and an *admin* to publish. `local` collapses
  this to one admin identity — perfect for a self-hosted instance. For a
  public site with many users, keep the upstream setup:
  `DOF_AUTH_BACKEND=clerk` plus Clerk env vars.
- **Costs.** Every question runs live against your key (typical answer:
  a handful of tool turns, thousands of tokens). Runs are stored in the local
  SQLite DB for inspection and eval.
- **Attribution.** `app.py`, `store.py`, `service.py`, `contracts.py`,
  `markdown_render.py`, `clerk_auth.py` and the UI styling/scripts are adapted
  from [CodeandoGuadalajara/dof-rag](https://github.com/CodeandoGuadalajara/dof-rag)
  `human_eval/` (MIT, Copyright 2025 Codeando Guadalajara). See the repo
  `LICENSE`.
