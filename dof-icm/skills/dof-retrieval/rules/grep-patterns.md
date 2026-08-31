# Grep Patterns for Legal Questions

## Basic patterns

```bash
# Exact phrase
grep -r "salario mínimo" corpus/2025/

# Multiple terms (AND)
grep -r "salario mínimo" corpus/2025/ | grep "zona libre"

# Multiple terms (OR)
grep -rE "salario mínimo|remuneración" corpus/2025/

# Case-insensitive
grep -ri "tipo de cambio" corpus/2026/
```

## Advanced patterns

```bash
# Numbers (e.g., amounts, percentages)
grep -rE "[0-9]+(\.[0-9]+)?\s*(pesos|por\s*cento|%)" corpus/2025/

# Dates
grep -rE "(enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|octubre|noviembre|diciembre)\s+de\s+20[0-9]{2}" corpus/2025/

# Legal article references
grep -rE "Art[íi]culo\s+[0-9]+" corpus/2025/

# "Transitorio" (transitional provisions)
grep -r "transitorio" corpus/2025/
```

## Tips

- **Start broad, narrow down.** First grep the whole year, then add more specific terms.
- **Use line numbers.** `grep -n` gives you line numbers for citations.
- **Count hits first.** `grep -r "term" corpus/ | wc -l` to see if the term is common or rare.
- **Check the index.** Before grepping, read `corpus/index/by-year-YYYY.md` to see what's in that year.

## Common pitfalls

- **Accents matter.** "salario" ≠ "salário". Be consistent.
- **Plural vs. singular.** "salarios" ≠ "salario". Try both.
- **Synonyms.** "remuneración" = "salario" in some contexts. "tipo de cambio" = "cambio" in others.
- **AVISO files.** `*_AVISO_*.doc` are notices, not substantive law. Usually less relevant for legal questions.
