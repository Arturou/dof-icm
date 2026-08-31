# Citation Format

Every factual claim in the final answer must cite a specific DOF document.

## Format

```
[Document title or short description] (DOF, YYYY-MM-DD, SECTION) — `relpath` — lines X–Y
```

## Examples

**Single doc:**
> El salario mínimo general diario para 2026 es de $315.04 por jornada diaria.
> [Acuerdo por el que se establecen los salarios mínimos 2026] (DOF, 2025-12-09, MAT) — `2025/12/09122025/MAT/006_DOF_20251209_MAT_5775533.md` — lines 42–48

**Multiple docs:**
> El tipo de cambio para 2006 fue $10.8386 MXN/USD [Acuerdo BdeM] (DOF, 2006-08-10, MAT) — `2006/08/10082006/MAT/005_DOF_20060810_MAT_4927660.md` — lines 12–15,
> y se mantuvo en $10.8386 para 2007 [Acuerdo BdeM] (DOF, 2007-08-09, MAT) — `2007/08/09082007/MAT/004_DOF_20070809_MAT_5123456.md` — lines 8–11.

## Rules

1. **relpath is required.** The path from `corpus/` root (e.g., `2025/12/09122025/MAT/006_...md`).
2. **Line range is required.** The specific lines where the fact appears (use `grep -n` to find them).
3. **Publication date is required.** From the filename (`DOF_YYYYMMDD_`) or the doc header.
4. **Section is required.** MAT or VES.
5. **No line range for multi-doc summaries.** If you're summarizing across many lines, cite the doc + the relevant section heading (e.g., "Artículo 3").
6. **"Not found" citation.** If the corpus doesn't contain the answer, cite the search you tried:
   > No se encontró en el corpus (2024–2026). Búsqueda: `grep -r "term" corpus/` → 0 hits.

## What NOT to cite

- AVISO files (`*_AVISO_*`) for substantive legal claims (they're notices, not law)
- Docs outside the 2024–2026 range (the corpus doesn't include them)
- "General knowledge" — if it's not in a cited doc, it's not in the answer
