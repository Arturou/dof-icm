# Navigate by Year & Section

## When to use
- The question mentions a specific year or date
- The question references a legal area that maps to a DOF section

## DOF sections

| Section | Content | Typical legal areas |
|---------|---------|---------------------|
| **MAT** | Materia (substantive law) | Labor law, tax, commercial, civil, administrative regulations |
| **VES** | Aviso (notices) | Court announcements, auction notices, public calls |

## Index maps

| File | What it tells you |
|------|-------------------|
| `corpus/index/by-year-YYYY.md` | All documents published in year YYYY, grouped by month, with doc counts and title samples |
| `corpus/index/by-section-MAT.md` | All MAT documents, grouped by year, with doc counts |
| `corpus/index/by-section-VES.md` | All VES documents, grouped by year, with doc counts |
| `corpus/index/recent.md` | Documents from the last 30 days |

## Strategy

1. **Year in the question?** → start with `by-year-YYYY.md`. If the question says "2026" or "current", check 2025 and 2026.
2. **Legal area in the question?** → map to MAT or VES (see table above).
3. **No clear year or section?** → start with `recent.md` and grep broadly.
4. **Narrow down:** once you have a year + section, grep `corpus/YYYY/..../SECTION/` for the key terms.

## Common legal-term → section mapping

| Term | Section |
|------|---------|
| salario, trabajo, laboral | MAT |
| impuesto, SAT, fiscal | MAT |
| comercio, mercantil | MAT |
| civil, familia | MAT |
| administrativo, regulación | MAT |
| concurso, remate, subasta | VES |
| judicial, notificación | VES |
| convocatoria, licitación | VES |
