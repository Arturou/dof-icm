# Answer Quality Standard

## What a good DOF answer looks like

1. **Direct.** Answers the question that was asked, not a nearby question.
2. **Complete.** Includes all relevant figures, dates, conditions, and caveats.
3. **Cited.** Every factual claim points to a specific doc + line range.
4. **Verbatim.** Amounts, dates, and legal text are copied exactly from the doc (no paraphrasing of figures).
5. **Unambiguous.** Resolves any date/amount ambiguity (e.g., "vigente desde el 1 de enero de 2026").
6. **Honest.** If the corpus doesn't contain the answer, says so — no fabrication.

## Common quality failures

| Failure | Example | Fix |
|---------|---------|-----|
| **Paraphrased figures** | "aproximadamente $315" | Copy verbatim: "$315.04" |
| **Missing date** | "el salario mínimo es $315.04" | Add: "vigente desde el 1 de enero de 2026" |
| **Wrong doc cited** | Citing a 2024 doc for a 2026 question | Verify the doc's publication date + effective date |
| **Answering a different question** | Q: "¿cuánto es?" A: "se establece en el Artículo 3" | Answer the question, then cite |
| **Fabricated lines** | Citing lines 50–55 when the fact is on lines 12–15 | Use `grep -n` to find the actual lines |
| **Missing caveat** | Stating a transitorio rule as permanent | Note: "transitorio, aplica solo para 2025" |

## Multi-doc answers

- Cite **each** doc separately.
- If docs conflict, state the conflict and which one is more recent/authoritative.
- If the answer requires calculation, show the math and cite both inputs.

## "Not found" answers

- State clearly: "No se encontró en el corpus (2024–2026)."
- Cite the search you tried (commands + hit counts).
- Suggest where the answer *might* be (e.g., "posiblemente en un documento anterior a 2024, no incluido en este corpus").
- Do **not** guess or fabricate.
