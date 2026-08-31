# Multi-Document Questions

## When to use
- The question references multiple legal provisions
- The answer requires cross-referencing (e.g., "What does Article X say about Y, and how does that interact with Z?")
- The question spans multiple years (e.g., "How has the minimum wage changed from 2024 to 2026?")

## Strategy

1. **Identify all sub-questions.** Break the question into atomic parts.
2. **Locate candidates for each sub-question.** Run the locate stage separately for each part.
3. **Merge candidate lists.** Deduplicate, rank by relevance to the *overall* question.
4. **Verify cross-references.** In the verify stage, check that the docs actually reference each other.

## Example

**Question:** "¿Cuál es el salario mínimo general y el de la Zona Libre de la Frontera Norte para 2026, y cómo cambió respecto a 2025?"

**Sub-questions:**
1. What is the minimum wage for 2026? (general + Zona Libre)
2. What was the minimum wage for 2025? (general + Zona Libre)
3. How do they compare? (calculation, not a doc lookup)

**Locate:**
- Sub-Q1: grep `corpus/2025/` + `corpus/2026/` for "salario mínimo" + "zona libre" → find the 2026 decree
- Sub-Q2: grep `corpus/2024/` for "salario mínimo" + "2025" → find the 2025 decree
- Sub-Q3: no doc needed; calculate from the two decrees

**Verify:**
- Read both decrees, extract the amounts, compute the % change
- Cite both docs in the answer

## Common multi-doc patterns

| Pattern | Example |
|---------|---------|
| **Change over time** | "How has X changed from year A to year B?" |
| **Cross-reference** | "What does Article X say, and how does Article Y modify it?" |
| **Definition + application** | "What is a 'servidor público', and what are the sanctions for corruption?" |
| **Condition + consequence** | "Under what conditions can X be revoked, and what are the effects?" |
