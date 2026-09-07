# DOF-ICM Evaluation

Year-scoped eval set for the file-based retrieval workspace.

## The set

`eval/questions.jsonl` — **28 questions**, all with gold documents published **2024–2026** (32 gold docs). Extracted from the upstream `dof-rag` v4 eval set (`eval/dof_queries_v4.jsonl`) by keeping only questions whose gold docs are fully in range. Same 7-category taxonomy:

| Category | Count | What it tests |
|----------|-------|---------------|
| single_passage | 4 | One doc answers directly |
| list_enumeration | 5 | Enumerate items from one doc |
| temporal_transitorio | 4 | Effective dates, transitorios, vigencia |
| cross_reference | 4 | Doc references another law/procedure |
| multi_document | 3 | 2–3 docs needed (change over time) |
| monitoring | 3 | What was published on a given date |
| negative_false_premise | 5 | Reject a false premise; answer correctly |

`eval/questions_v2.jsonl` — **44 questions** (the same set, extended: adds 16 hand-picked 2024–2026 questions and an `ambiguity`/`valid_alternatives` schema for decrees that share identical text).

`eval/questions_fiscal.jsonl` — **12 preguntas fiscales/SAT** (2024–2026) orientadas a contribuyentes: persona física con actividad empresarial (deducción inmediata del Decreto "Plan México"), persona moral/tesorería (Ley de Ingresos, endeudamiento), contador/asesor fiscal (Resolución Miscelánea Fiscal 2025/2026 y sus modificaciones de julio 2026, reducción de multas, anexos). Misma taxonomía de 7 categorías; todas las citas gold verificadas verbatim contra el corpus. Corridas de referencia: `eval/results/fiscal_deepseek_v4_flash.jsonl`.

## Resultados de referencia (scores)

Corridas con `deepseek-v4-flash` (API). Métricas: *completed* (terminó con respuesta), *doc-hit* (relpath citado ∈ gold, ambiguity-aware), *semantic* (cifras clave de la referencia en la respuesta — heurística estricta, la métrica primaria es doc-hit).

| Set | n | Doc-hit | Completed | Semantic | Reporte |
|---|---|---|---|---|---|
| `questions_fiscal.jsonl` (fiscal/SAT 2024–2026) | 12 | **12/12 (100%)** | 12/12 (100%) | 10/12 (83%) | [`report-fiscal-deepseek.md`](report-fiscal-deepseek.md) |
| `questions_v2.jsonl` (general) | 44 | **40/44 (91%)** | 42/44 (95%) | 21/44 (48%) | [`report-benchmark-v2.md`](report-benchmark-v2.md) |

El benchmark v2 comparó además `qwen/qwen3.8-27b` local (LM Studio) de forma **parcial** (24/44; la máquina 4090 se cayó dos veces) — ver caveats en `report-benchmark-v2.md`.

## Scoring (ICM-style, no chunks)

The upstream v4 set scores chunk-level recall. ICM has no chunks — the retrieval unit is the **document**. Score each run on:

1. **Doc-level hit (R@k):** does the agent's located candidate set (stage 01 output) contain the gold `relpath`? Check top-1, top-5, top-10.
2. **Answer correctness:** does the final answer (stage 02 output) contain the reference answer's key figures/dates, with a correct citation?
3. **Citation precision:** is the cited relpath actually one of the gold docs (or a defensible equivalent)?

Run logs land in `eval/results/[timestamp]-[model]-run.md`, one per question.

## How to run

Point the agent at this workspace with the recommended model config, and run each question through the two stages. Script a harness loop if your agent framework supports it; otherwise run interactively.

Suggested smoke set (1 per category): SP-001, LI-002, TE-003, CR-005, MD-002, MO-005, NE-005.

## Baselines y comparativa

- **Comparativa ICM vs RAG original:** [`report-icm-vs-rag.md`](report-icm-vs-rag.md) — mismas 56 preguntas y mismo corpus (2024–2026): el agente ICM cita el documento dorado en **52/56 (93%)**; el recuperador léxico clásico del RAG original (BM25 FTS5, una fila por documento — configuración favorable al baseline) lo coloca en su top-10 en **24/56 (43%)** y top-50 en **41/56 (73%)**, MRR 0.289. En las 28 preguntas compartidas con el eval v4 upstream: ICM 25/28 (89%) vs BM25 top-10 10/28 (36%).
- Baseline reproducible: `python eval/bm25_baseline.py --corpus corpus --questions eval/questions_v2.jsonl eval/questions_fiscal.jsonl --db var/bm25_eval.sqlite --out eval/results/bm25_baseline.json` (resultados en `eval/results/bm25_baseline.json`, gitignored).
- Upstream dof-rag v4 (RAG completo BM25+vectores+híbrido, corpus 1999–2026): MRR 0.339 / all-hop@20 0.595 / doc any-gold@10 0.476 sobre las 42 preguntas — métricas de **recuperación**, no end-to-end (de `dof-rag/dof-rag/reports/eval_v4_retrieval.md`).
- Apples-to-apples solo en las 28 preguntas en rango; las cifras upstream son sobre las 42 (14 citan documentos 2006–2022, fuera del corpus ICM).

## Extending

- Hand-pick more 2024–2026 questions (Option A), or regenerate a proper v5 with the v3/v4 methodology constrained to 2024–2026 gold docs (Option B, later).
