---
name: dof-retrieval
description: Locate relevant documents in the DOF corpus (2024–2026) for a legal question.
metadata:
  tags: dof, mexican-law, retrieval
---

# DOF Retrieval Skill

Use this skill whenever you need to find documents in the DOF corpus that answer a legal question.

## How to use

1. **Classify the question** — identify the year, section (MAT/VES), and key legal terms.
2. **Load the navigation maps** — read `corpus/index/by-year-YYYY.md` and/or `corpus/index/by-section-SECTION.md` to narrow the scope.
3. **Grep the corpus** — use the legal terms as search patterns over `corpus/YYYY/...`.
4. **Rank candidates** — pick the 3–10 most relevant docs based on term frequency, recency, and section fit.
5. **Write candidates** — save to `stages/01-locate/output/[slug]-candidates.md` using the format below.

## Rule files

Read the relevant rule file(s) for your question type:

- [rules/navigate-year-section.md](rules/navigate-year-section.md) — how to use the index maps to narrow scope
- [rules/grep-patterns.md](rules/grep-patterns.md) — effective grep patterns for legal questions
- [rules/multi-doc-questions.md](rules/multi-doc-questions.md) — questions that require multiple documents
- [rules/temporal-questions.md](rules/temporal-questions.md) — "as of date", "current", "transitorio" questions

## Output format (candidates file)

```markdown
# Candidates for: [question]

## Question classification
- **Year hint:** 2025 (from question text)
- **Section hint:** MAT (from legal terms)
- **Key terms:** "salario mínimo", "zona libre frontera norte"

## Candidates
| # | Relpath | Publication date | Section | Why it matches |
|---|---------|-----------------|---------|----------------|
| 1 | 2025/12/09122025/MAT/006_DOF_20251209_MAT_XXXXXXX.md | 2025-12-09 | MAT | Mentions "salarios mínimos 2026" + "zona libre" |
| 2 | ... | ... | ... | ... |

## Search trail
- `grep -r "salario mínimo" corpus/2025/` → 12 hits
- `grep -r "zona libre frontera" corpus/2025/MAT/` → 3 hits
- Selected top 5 by relevance
```
