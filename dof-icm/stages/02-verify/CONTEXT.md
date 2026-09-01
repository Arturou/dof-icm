# Stage 02 — Verify

Read the candidate docs, extract the answer, and verify it against the question.

## Inputs

| Source | File/Location | Section/Scope | Why |
|--------|--------------|---------------|-----|
| Candidates | `../01-locate/output/[slug]-candidates.md` | Full file | The docs to read |
| Candidate docs | `corpus/[relpath]` | Lines cited in candidates | The actual text |
| Answer quality | `references/answer-quality.md` | Full file | What a good answer looks like |
| Citation format | `../01-locate/references/citation-format.md` | Full file | How to cite |

## Process

1. **Read each candidate doc.**
   - Open the file at the cited line range (±10 lines for context).
   - Extract the exact text that answers the question.

2. **Verify against the question.**
   - Does the doc actually answer the question? (Not just mention the terms.)
   - Is the date correct? (Effective date vs. publication date.)
   - Is the amount/figure exact? (Copy it verbatim from the doc.)
   - If multiple docs, do they agree? If they conflict, note the conflict.

3. **Draft the answer.**
   - Answer the question directly, in the language of the question.
   - Cite every factual claim (see `citation-format.md`).
   - If the answer requires calculation (e.g., % change), show the math.
   - If the corpus doesn't contain the answer, say so clearly.

4. **Write the answer file.**
   - Save to `output/[slug]-answer.md` using the format below.

## Outputs

| Artifact | Location | Format |
|----------|----------|--------|
| Answer | `output/[slug]-answer.md` | Markdown: answer + citations + verification notes |

## Answer format

```markdown
# Answer to: [question]

## Answer
[Direct answer, in the language of the question. Cite every claim.]

## Citations
1. [Doc title] (DOF, YYYY-MM-DD, SECTION) — `relpath` — lines X–Y
2. ...

## Verification
- [ ] Doc 1 directly answers the question: YES/NO — [note]
- [ ] Date is correct: YES/NO — [note]
- [ ] Amount/figure is verbatim from the doc: YES/NO — [note]
- [ ] No conflicting docs found: YES/NO — [note]

## Notes
[Any caveats, conflicts, or "not found" explanations.]
```

## Checkpoint

**Before writing output:** ask yourself — "Can a reader verify this answer by following the citations?" If not, fix the citations. "Am I answering the question that was asked, or a nearby question?" If not, re-read the question.

## Negative-premise protocol (questions that assert a premise)

Some questions assert a premise ("why did X happen", "when was X abrogated", "what did X establish") that may be **false** or only partially true. Handle them in this order, then STOP:

1. **Extract the premise.** What fact does the question assume? (e.g. "the UMA began applying Jan 1" / "the Water Law was fully abrogated").
2. **Verify the premise against the docs you have.** One targeted read or grep is enough. Do NOT keep searching for more confirmation once the doc answers it.
3. **Answer with correction.** If the premise is true → answer normally. If false or partial → state the correction explicitly FIRST, cite the contradicting doc (relpath + lines), then answer the corrected question.
4. **Record premise status** in the answer file:
   `premise_status: true | false | partial`
   Add one audit line: `- [ ] Premise verified against a cited doc: YES/NO — [note]`
5. **STOP after step 3.** Do not grep the same terms again ("abroga"/"deroga"/"vigente") to double-check — the cited doc is the source of truth.

## Audit

- [ ] Answer directly addresses the question (not a nearby question)
- [ ] Every factual claim has a citation (relpath + line range + date + section)
- [ ] Amounts/figures are copied verbatim from the cited lines
- [ ] Date ambiguity is resolved (effective date stated explicitly)
- [ ] Conflicts between docs are noted (if any)
- [ ] If "not found", the search trail is cited
- [ ] Language matches the question's language
