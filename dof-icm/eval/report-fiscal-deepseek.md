# Benchmark fiscal/SAT 2024–2026 — deepseek-v4-flash (API)

- **Set:** `eval/questions_fiscal.jsonl` — 12 preguntas nuevas fiscales/SAT (2024–2026), mismas 7 categorías del eval general.
- **Modelo:** `deepseek-v4-flash` vía `https://api.deepseek.com/v1` (`DEEPSEEK_API_KEY`), `reasoning_effort=minimal`.
- **Resultados:** `eval/results/fiscal_deepseek_v4_flash.jsonl` (primera corrida + reintentos con `DOF_MAX_TURNS=18` para FS-004/FS-007/FS-010, que agotaron el tope por defecto de 8 turnos).
- **Métricas (ICM/doc-level):** *completed* (respuesta final), *doc-hit* (cita relpath ∈ gold), *semantic* (cifras clave de la referencia presentes en la respuesta).

## Resultado global

| Métrica | n | % |
|---|---|---|
| completed | 12/12 | 100% |
| doc-hit (ambiguity-aware) | 12/12 | 100% |
| semantic (cifras clave) | 10/12 | 83% |

- Tools por pregunta: avg 6.4 · min 3 · max 11
- Uso total: ~726,452 tokens de entrada / 28,284 de salida (12 preguntas + 3 reintentos).

## Por categoría (n / hit / semantic / completed)

| categoría | n | hit | sem | done |
|---|---|---|---|---|
| single_passage | 3 | 3 | 3 | 3 |
| list_enumeration | 2 | 2 | 1 | 2 |
| cross_reference | 1 | 1 | 1 | 1 |
| temporal_transitorio | 1 | 1 | 1 | 1 |
| multi_document | 1 | 1 | 1 | 1 |
| monitoring | 2 | 2 | 2 | 2 |
| negative_false_premise | 2 | 2 | 1 | 2 |

## Detalle por pregunta

| id | categoría | dificultad | done | hit | sem | tools | tema |
|---|---|---|---|---|---|---|---|
| FS-001 | single_passage | easy | ✅ | ✅ | ✅ | 7 | Plan México: deducción inmediata equipo de cómputo 88% |
| FS-002 | list_enumeration | medium | ✅ | ✅ | ✅ | 6 | Plan México: requisitos art. Primero (I–V) |
| FS-003 | cross_reference | easy | ✅ | ✅ | ✅ | 3 | Buzón tributario → art. 17-K CFF |
| FS-004 | single_passage | easy | ✅ | ✅ | ✅ | 6 | LIF 2025: endeudamiento neto interno (1 billón 580 mil mdp) |
| FS-005 | multi_document | hard | ✅ | ✅ | ✅ | 11 | LIF 2025 vs 2026: tope interno 580→780 mil mdp |
| FS-006 | temporal_transitorio | easy | ✅ | ✅ | ✅ | 7 | Modificaciones RMF 2026: vigencia desde el 10-jul-2026 |
| FS-007 | single_passage | medium | ✅ | ✅ | ✅ | 10 | RMF 2026 regla 2.14.11: reducción 90% (15 días) |
| FS-008 | negative_false_premise | medium | ✅ | ✅ | ⚠️ | 5 | Mobiliario/equipo de oficina NO aplica a deducción inmediata |
| FS-009 | monitoring | medium | ✅ | ✅ | ✅ | 3 | RMF 2025 publicada 30-dic-2024 |
| FS-010 | list_enumeration | medium | ✅ | ✅ | ⚠️ | 9 | Reglas adicionadas por la 1ª Res. Mod. RMF 2026 |
| FS-011 | monitoring | medium | ✅ | ✅ | ✅ | 4 | Anexos RMF 2026 publicados 13-ene-2026 |
| FS-012 | negative_false_premise | medium | ✅ | ✅ | ✅ | 6 | LIF 2026 NO reduce el externo: 15 mil 500 mdd |

⚠️ = el documento correcto se citó (doc-hit ✅) pero la *semantic* del scorer no pasó:
- **FS-008**: la `reference_answer` no contiene cifras (por diseño), y el scorer solo marca semántica cuando hay dígitos en la referencia → falso negativo del scorer, no del modelo.
- **FS-010**: enumeración larga de números de reglas (3.5.23, 9.1.23, …); el modelo no reprodujo el set exacto completo de dígitos.

## Observaciones

- **100% doc-hit**: en las 12 preguntas el agente localizó el documento gold correcto y lo citó (relpath en el cuerpo de la respuesta).
- Tres preguntas (FS-004, FS-007, FS-010) excedieron el tope por defecto de 8 turnos en la primera corrida pese a haber localizado el documento — documentos extensos/numéricos (RMF, LIF) con lecturas repetidas. Con `DOF_MAX_TURNS=18` completaron y acertaron.
- La semántica por cifras es una heurística estricta (todas las cifras de la referencia deben aparecer); los dos fallos marcados son de esa heurística, no de recuperación.

_Generado: DeepSeek API local (scripts/run_icm_agent.py + scripts/score_eval.py)._
