# ICM vs. RAG clásico (dof-rag): comparativa

**Fecha:** 2026-09 (corrida BM25 de referencia sobre el corpus ICM).

**Pregunta:** ¿el método ICM (archivos + agente en dos etapas) mejora frente al
enfoque RAG original propuesto en `dof-rag` (BM25 + vectores + fusión híbrida)?

**Veredicto corto:** sí, dentro del rango del corpus ICM (**2024–2026**). Sobre
las **mismas preguntas y el mismo corpus**, el agente ICM termina citando el
documento dorado en **52/56 (93%)**, mientras que el recuperador léxico clásico
(BM25, la pieza central del RAG original) coloca el documento dorado en su
top-10 en **24/56 (43%)** y en su top-50 en **41/56 (73%)**. La mejora no es
gratis: ICM requiere un LLM multi-paso (~6 llamadas a herramientas, ~50–63k
tokens de entrada por pregunta) y su corpus cubre solo 2024–2026, mientras que
el RAG original cubría 1999–2026. Ver limitaciones al final.

---

## 1. Qué se compara (y qué no)

| | RAG original (`dof-rag`) | ICM (`dof-icm`) |
|---|---|---|
| Corpus | 657,867 docs, 1999-01-04 → 2026-04-24 (markdown + OCR) | 52,168 docs markdown, 2024-01-02 → 2026-08-31 |
| Unidad de recuperación | chunks (`dof-chunker-v1`; 6,730,304 chunks indexados) | documentos (archivos .md completos) |
| Índices | SQLite FTS5 (BM25) + vec0 binario (embeddings GGUF jina v5 small) + fusión híbrida ponderada | ninguno: índice de títulos .md + `grep_corpus` + `read_file` (búsqueda guiada por el agente) |
| Etapas | recuperación determinista (BM25/vectores/híbrido) expuesta como herramientas + bucle de agente acotado (≤8 turnos) | dos: 01-locate (localiza candidatos) → 02-verify (lee, extrae, verifica y cita el texto) |
| Salida | respuesta + trazas | respuesta markdown con **citas `relpath` verificables** |
| Métricas publicadas | **solo recuperación** (doc/evidence recall, MRR, all-hop) | **end-to-end** (completed / doc-hit / semantic) |
| Evaluación | v3 (3,013 queries sintéticas), v4 (42 curadas, 7 categorías); respuestas finales evaluadas por humanos en el sitio | 44 preguntas generales (v2) + 12 fiscales/SAT (FS), todas con gold docs verificados verbatim |

El proyecto original **no publicó un benchmark numérico de respuestas finales**
(el script `scripts/eval_v4_agent.py` existe; sus outputs no están versionados;
la evaluación de respuestas era humana vía el sitio `human_eval/`). Por eso la
comparación cuantitativa se hace en dos planos:

1. **Mismo corpus y mismas preguntas (esta corrida):** BM25 sobre el corpus ICM
   (52,168 docs, una fila por documento) evaluado con las 56 preguntas doradas
   de ICM, contra el `doc-hit` end-to-end del agente ICM. Como BM25 es un
   recuperador *de una sola pasada*, se reporta como top-k (doc-any@k, MRR).
2. **Contexto publicado por el RAG original:** sus métricas de recuperación v4
   sobre su corpus completo de 27 años (sección 4).

> Nota de justicia comparativa: indexar *documentos completos* (en vez de
> chunks) favorece al baseline BM25 a nivel documento, y el `doc-hit` de ICM es
> una métrica más exigente que "aparecer en top-k": exige que el agente termine,
> decida qué documento es el correcto **y lo cite con su relpath**. Aun así ICM
> supera al baseline.

## 2. Misma corpus, mismas preguntas (56 = 44 v2 + 12 fiscales)

Corrida nueva: `eval/bm25_baseline.py` (SQLite FTS5, `unicode61 remove_diacritics
1`, MATCH OR sin stemming — misma receta que el reporte de recuperación del RAG
original) sobre el corpus ICM. Resultados: `eval/results/bm25_baseline.json`
(gitignored). DeepSeek `deepseek-v4-flash` para ICM (corridas ya documentadas).

### 2.1 Totales

| Sistema | n | Doc @1 | @5 | @10 | @20 | @50 | MRR | *completed / doc-hit* |
|---|---|---:|---:|---:|---:|---:|---:|---|
| BM25 (baseline clásico) | 56 | 12 (21%) | 21 (38%) | 24 (43%) | 31 (55%) | 41 (73%) | 0.289 | — |
| BM25 — v2 (44) | 44 | 10 (23%) | 15 (34%) | 18 (41%) | 22 (50%) | 31 (70%) | 0.284 | — |
| BM25 — fiscal (12) | 12 | 2 (17%) | 6 (50%) | 6 (50%) | 9 (75%) | 10 (83%) | 0.309 | — |
| **ICM (deepseek-v4-flash)** | 56 | — | — | — | — | — | — | **54 / 52 (93%)** |
| ICM — v2 (44) | 44 | — | — | — | — | — | — | 42 / 40 (91%) |
| ICM — fiscal (12) | 12 | — | — | — | — | — | — | 12 / 12 (100%) |

Incluso dando al BM25 hasta **50 documentos** por pregunta (73%), no alcanza el
doc-hit del agente (93%). Contingencia a nivel de pregunta (56):

- ICM acierta y BM25 falla en su top-10: **30** preguntas (14 de ellas ni en su
  top-50).
- Ambos aciertan: 22. Ambos fallan en top-10: 2 (CR-003, SP2-002).
- BM25 acierta en top-10 e ICM no cita el dorado: **2** (CR-004 y NE-006 — ver
  §3: aquí la recuperación clásica sí encontró el documento y el agente ICM no
  lo citó correctamente).

### 2.2 Subconjunto compartido con el eval v4 del RAG original (28 preguntas)

De las 42 preguntas curadas de v4, **28 tienen todos sus documentos dorados en
2024–2026** y fueron portadas 1:1 a ICM (`eval/questions.jsonl` ⊂
`questions_v2.jsonl`, mismos ids y mismos relpaths gold). Las otras 14 citan
documentos de 2006–2022, fuera del alcance del corpus ICM.

| Sistema | n | @1 | @5 | @10 | @20 | @50 | doc-hit |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| BM25 sobre corpus ICM | 28 | 4 (14%) | 7 (25%) | 10 (36%) | 13 (46%) | 18 (64%) | — |
| **ICM** | 28 | — | — | — | — | — | **25 (89%)** |

Por categoría (28 compartidas):

| Categoría | n | ICM doc-hit | BM25 @10 | BM25 @50 |
|---|---:|---:|---:|---:|
| single_passage | 3 | 3 | 3 | 3 |
| list_enumeration | 5 | 5 | 0 | 4 |
| temporal_transitorio | 4 | 4 | 1 | 2 |
| cross_reference | 4 | 2 | 1 | 1 |
| multi_document | 3 | 3 | 2 | 3 |
| monitoring | 4 | 4 | 1 | 1 |
| negative_false_premise | 5 | 4 | 2 | 4 |
| **Total** | **28** | **25 (89%)** | **10 (36%)** | **18 (64%)** |

El BM25 pierde de forma sistemática donde la pregunta **parafrasea** o pide
**enumerar** (list_enumeration: 0/5 en top-10) o exige **vigilancia por fecha**
(monitoring: 1/4; en 2 de 4 el dorado ni aparece en su top-50); ICM resuelve
todas esas. Donde BM25 suele acertar (single_passage con términos literales)
ambos aciertan.

### 2.3 Por categoría, set completo (56 = 44 v2 + 12 fiscales)

| Categoría | n | ICM doc-hit | BM25 @10 | BM25 @50 |
|---|---:|---:|---:|---:|
| single_passage | 10 | 9 (90%) | 7 (70%) | 9 (90%) |
| list_enumeration | 9 | 9 (100%) | 3 (33%) | 8 (89%) |
| temporal_transitorio | 7 | 7 (100%) | 3 (43%) | 5 (71%) |
| cross_reference | 7 | 5 (71%) | 1 (14%) | 2 (29%) |
| multi_document | 6 | 6 (100%) | 4 (67%) | 6 (100%) |
| monitoring | 8 | 8 (100%) | 2 (25%) | 3 (38%) |
| negative_false_premise | 9 | 8 (89%) | 4 (44%) | 8 (89%) |
| **Total** | **56** | **52 (93%)** | **24 (43%)** | **41 (73%)** |

## 3. Fallos del agente ICM (transparencia)

Los 4 no-doc-hit de ICM en v2 (el set fiscal quedó 12/12):

- **CR-003** (cross_reference, caso `ambiguity`): completó pero citó dos decretos
  relacionados (2025-03-24 y 2026-04-20) que no están entre el gold ni los
  `valid_alternatives`. El BM25 tampoco encontró el dorado (rank 72).
- **CR-004** (cross_reference): sin completar (sin `stop_reason=completed`). El
  BM25 sí lo tenía en rank 4 → fallo del agente, no de disponibilidad del doc.
- **NE-006** (negative_false_premise): completó pero citó el decreto del
  2026-04-20; el dorado correcto (2026-04-17) existía y el BM25 lo tenía en
  rank 7 → fallo de selección/verificación del agente.
- **SP2-002** (single_passage): sin completar.

Conclusión: el `doc-hit` de ICM no es solo "el techo de recuperación"; en
CR-004 y NE-006 la recuperación clásica acertó y el agente no cerró bien. Los
fallos restantes de ICM se concentran en cross_reference (2/7 de la 56) y en la
heurística `semantic` ya documentada (no es métrica de recuperación).

## 4. Contexto: métricas publicadas del RAG original (su corpus, 27 años)

Del eval v4 del proyecto original (`dof-rag/dof-rag/reports/eval_v4_retrieval.md`
y `eval/cache/eval_v4_full_comparison.json`, 42 preguntas, corpus completo):

| Sistema (original) | MRR | Doc any-gold @10 | Doc R@10 | All-hop @20 |
|---|---:|---:|---:|---:|
| BM25 puro | 0.221 | 0.452 | 0.429 | 0.429 |
| Vector (jina-binary) | 0.284 | 0.500 | 0.476 | 0.476 |
| Híbrido W0.5 (BM25+vector) | **0.339** | 0.476 | 0.452 | **0.595** |

Estas cifras **no son directamente comparables** con las de ICM: son de
recuperación (no end-to-end), sobre un corpus 5× mayor en años (1999–2026), lo
que hace la recuperación más difícil (más candidatos), y sobre las 42 preguntas
(14 de ellas fuera del rango ICM). Se citan para situar el orden de magnitud del
RAG original: incluso su mejor híbrido colocaba el documento dorado en el top-10
solo ~la mitad de las veces en esas 42 preguntas, y la recuperación de evidencia
por chunk rondaba R@10 ≈ 0.34.

## 5. Comparativa cualitativa / operativa

| Dimensión | RAG original | ICM |
|---|---|---|
| Infraestructura | embeddings (GPU/GGUF), store de vectores vec0, SQLite FTS5, pesos híbridos, chunker versionado | solo archivos .md + índice de títulos .md; cero índices binarios |
| Construcción | pipeline de chunks + embeddings sobre 6.7M chunks; voluminoso y con estado (DBs derivadas) | `build_corpus.py` → markdown + títulos; reproducible y versionable |
| Costo por consulta | recuperación determinista local (casi gratis); consumo del LLM en el bucle del agente (no medido aquí) | ~6 llamadas a herramientas; ~50k (v2) / ~63k (fiscal) tokens de entrada y ~2.5k de salida por pregunta (deepseek-v4-flash) |
| Verificabilidad | herramientas deterministas de búsqueda (BM25/vector/híbrido) + traces del agente; evidencia = top-k de chunks | citas `relpath` + sección; la etapa 02 lee el documento y verifica la cita contra el texto |
| Errores típicos | riesgo de responder sin el documento correcto cuando el dorado no entra al top-k — en su propio eval: doc any-gold@10 0.45–0.50 y evidencia por chunk R@10 ≈ 0.34 | doc-hit 52/56 (93%); 2 fallos de selección (CR-003, NE-006) y 2 corridas sin completar (CR-004, SP2-002) |
| Alcance temporal | 1999–2026 (27 años) | 2024–2026 (ventaja: corpus acotado y verificable; desventaja: no responde docs anteriores) |
| Portabilidad | requiere entorno de embeddings + índices | copia la carpeta y lee CLAUDE.md/CONTEXT.md (ICM) con cualquier modelo |
| Reproducibilidad | evaluado a nivel recuperación | eval end-to-end con gold verbatim, scorer y reportes commitados |

**Qué mejoró con ICM:** localización del documento correcto en preguntas reales
(paráfrasis, listas, monitoreo por fecha, multi-documento, premisas falsas),
verificación/citas explícitas, ausencia total de índices/embeddings, y un
benchmark end-to-end reproducible. **Qué se perdió:** alcance temporal (el RAG
original cubre 1999 en adelante) y la velocidad/cero-costo de una sola pasada
léxica para preguntas triviales con términos literales.

## 6. Limitaciones del estudio

1. **Etapas distintas:** las métricas del RAG original son de recuperación
   (top-k); las de ICM son end-to-end. La corrida BM25 de la sección 2 cierra
   parcialmente esa brecha (misma corpus, mismas preguntas, misma unidad
   documento), pero es **una sola pasada léxica**, no el híbrido vectorial
   completo del proyecto original (que en su eval mejoró BM25: MRR 0.221→0.339).
   El híbrido sobre el corpus ICM probablemente superaría al BM25 puro; aun así,
   su techo publicado (~0.45–0.50 doc@10) está muy por debajo del doc-hit ICM.
2. **Corpus más chico:** ICM solo responde 2024–2026; 14 de las 42 preguntas v4
   originales citan documentos 2006–2022 y quedan fuera por diseño.
3. **Doc-level BM25 vs chunks:** una fila por documento favorece al baseline
   (ver nota en §1). Los ranks profundos (LI-006 rank 159, CR-006 rank 144,
   MO-005 rank 130) y los `rank=None` (dorado fuera del top-200) muestran que el
   problema no es de umbral, sino léxico-semántico.
4. **n pequeño:** 56 preguntas (28 compartidas con v4, 16 nuevas, 12 fiscales);
   los desgloses por categoría son orientativos.
5. **Semantic no se usa aquí** (heurística de cifras, no de recuperación).

## 7. Reproducción

```bash
# Baseline BM25 sobre el corpus ICM (una fila por documento, FTS5 unicode61
# remove_diacritics 1, OR sin stemming) + 56 preguntas
cd dof-icm
python eval/bm25_baseline.py --corpus corpus \
  --questions eval/questions_v2.jsonl eval/questions_fiscal.jsonl \
  --db var/bm25_eval.sqlite --out eval/results/bm25_baseline.json

# Scoring de las corridas ICM (doc-hit/completed/semantic)
python scripts/score_eval.py --questions eval/questions_v2.jsonl \
  --results eval/results/bench_deepseek.jsonl --tag deepseek-v4-flash
python scripts/score_eval.py --questions eval/questions_fiscal.jsonl \
  --results eval/results/fiscal_deepseek_v4_flash.jsonl --tag deepseek-v4-flash
```

Artefactos: script de baseline versionado en `eval/bm25_baseline.py`; resultados
en `eval/results/bm25_baseline.json` (gitignored junto con el resto de
`eval/results/`); números del RAG original citados desde
`dof-rag/dof-rag/reports/eval_v4_retrieval.md` y
`eval/cache/eval_v4_full_comparison.json` del subtree legacy.
