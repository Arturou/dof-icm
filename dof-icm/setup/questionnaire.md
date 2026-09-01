# DOF-ICM Setup

One-time onboarding. Answer these to configure the workspace. (All optional — defaults are fine for most users.)

## 1. Year range

**Default:** 2024–2026 (the corpus range)

- Do you want to restrict to a narrower range? (e.g., "only 2026")
- Do you want to extend beyond the corpus? (Not possible — the corpus is fixed at 2024–2026.)

## 2. Language

**Default:** Answer in the language of the question (corpus is Spanish)

- Do you always want Spanish answers?
- Do you always want English answers?
- Do you want bilingual answers (Spanish + English summary)?

## 3. Citation style

**Default:** `[Doc title] (DOF, YYYY-MM-DD, SECTION) — relpath — lines X–Y`

- Do you want a different citation format? (e.g., numbered footnotes, Chicago style)
- Do you want to include the DOF URL? (The corpus doesn't store URLs; we'd need to add them.)

## 4. Verbosity

**Default:** Complete but concise (answer + citations + verification)

- Do you want more detail? (e.g., full text of cited passages)
- Do you want less detail? (e.g., answer + first citation only)

## 5. Output location

**Default:** `stages/02-verify/output/[slug]-answer.md`

- Do you want answers in a different folder?
- Do you want answers appended to a running log?

## 6. Model config (for your harness)

The workspace prescribes this model, but your harness must be configured to use it:

```
provider: deepseek        # OpenAI-compatible API
endpoint: https://api.deepseek.com/v1
model: deepseek-v4-flash
api_key: $DEEPSEEK_API_KEY
```

- Is this correct for your setup?
- Do you want to use a different model? (The workspace is model-agnostic; any LLM can use it.)

---

**After answering:** save your choices to `setup/config.md` (create it). The agent will read `setup/config.md` on every run if it exists.
