# Temporal Questions

## When to use
- The question asks about the law "as of" a specific date
- The question asks what is "current" or "vigente"
- The question references "transitorio" (transitional) provisions
- The question asks about a law that has been amended or repealed

## Key concepts

| Term | Meaning |
|------|---------|
| **Vigente** | Currently in force |
| **Transitorio** | Transitional provision (usually one-time, applies for a limited period) |
| **Derogado** | Repealed / no longer in force |
| **Vigencia** | Effective date / period of force |

## Strategy

1. **Identify the reference date.** "As of 2026-01-01" → look for docs published before 2026-01-01 that are still in force on that date.
2. **Find the latest applicable doc.** Grep for the legal term in the most recent year(s) first.
3. **Check for amendments.** Look for newer docs that modify or repeal the provision.
4. **Check transitorios.** Read the "Transitorio" sections of relevant docs — they often specify effective dates and one-time rules.
5. **Cite the effective date.** In the answer, state explicitly which date the law was in effect.

## Example

**Question:** "¿Cuál es el salario mínimo general diario vigente en 2026?"

**Strategy:**
1. Reference date: 2026 (any date in 2026)
2. Grep `corpus/2025/` for "salario mínimo" + "2026" → find the Dec 2025 decree setting the 2026 wage
3. Grep `corpus/2026/` for "salario mínimo" → check if there's a 2026 amendment
4. Read the Dec 2025 decree, extract the amount ($315.04) and effective date (Jan 1, 2026)
5. Answer: "$315.04 por jornada diaria, vigente desde el 1 de enero de 2026" + cite

## Common pitfalls

- **"Vigente" ≠ "latest."** The latest doc might repeal or amend an earlier one. Always check for newer docs.
- **Transitorios are time-bound.** A transitorio provision might apply only for 2025, not 2026. Read the specific dates.
- **Multiple amendments.** A law might be amended 3 times. You need the *latest* amendment that's still in force.
- **Effective dates vs. publication dates.** A doc published in Dec 2025 might take effect in Jan 2026. Cite both.
