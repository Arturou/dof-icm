# Stage 01 — Locate

Find the DOF documents most likely to answer the question.

## Inputs

| Source | File/Location | Section/Scope | Why |
|--------|--------------|---------------|-----|
| User question | (provided in prompt) | Full text | The question to answer |
| Year index | `corpus/index/by-year-*.md` | Relevant year(s) | Narrow scope by year |
| Section index | `corpus/index/by-section-*.md` | MAT or VES | Narrow scope by section |
| Recent index | `corpus/index/recent.md` | Last 30 days | Quick check for very recent docs |
| Retrieval skill | `skills/dof-retrieval/SKILL.md` | Full skill + relevant rules/ | How to navigate + grep |

## Process

1. **Classify the question.**
   - Extract: year hint, section hint (MAT/VES), key legal terms.
   - Load the relevant `corpus/index/by-*.md` map(s).

2. **Grep the corpus.**
   - Use the patterns from `skills/dof-retrieval/rules/grep-patterns.md`.
   - Start broad (year + section), narrow down (specific terms).
   - Record the search trail (what you grepped, how many hits).

3. **Rank candidates.**
   - Pick the 3–10 most relevant docs.
   - Rank by: term frequency, recency, section fit.
   - Prefer substantive law (MAT) over notices (VES) for legal questions.

4. **Write the candidates file.**
   - Save to `output/[slug]-candidates.md` using the format in `skills/dof-retrieval/SKILL.md`.
   - Include the question classification, the ranked candidates table, and the search trail.

## Outputs

| Artifact | Location | Format |
|----------|----------|--------|
| Candidates | `output/[slug]-candidates.md` | Markdown: classification + ranked table + search trail |

## Checkpoint

**Before writing output:** ask yourself — "Do I have at least one doc that *directly* addresses the question?" If not, broaden the search (different terms, adjacent years, both MAT and VES). If still nothing, note that in the candidates file and proceed to stage 02 to report "not found".

## Audit

- [ ] At least 1 candidate doc (or explicit "not found" note)
- [ ] Each candidate has a "why it matches" justification
- [ ] Search trail is recorded (commands + hit counts)
- [ ] Year + section classification is explicit
- [ ] No fabricated doc paths (every relpath must exist in `corpus/`)
