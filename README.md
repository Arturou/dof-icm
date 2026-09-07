# DOF-ICM — Q&A sobre el Diario Oficial de la Federación (2024–2026)

> **English summary.** This repository (a fork of
> [CodeandoGuadalajara/dof-rag](https://github.com/CodeandoGuadalajara/dof-rag))
> hosts two related projects in two folders:
>
> - **[`dof-icm/`](dof-icm/README.md)** — *new, recommended.* A portable,
>   file-based, RAG-free Q&A workspace over the Mexican *Diario Oficial de la
>   Federación* (DOF, 2024–2026). The corpus is plain markdown; retrieval is a
>   skill; no embeddings, no vector DB, no server. Ships a self-contained web
>   UI ([`dof-icm/web/`](dof-icm/web/README.md)) that answers with **your own
>   API key**.
> - **[`dof-rag/`](dof-rag/README.md)** — *legacy.* The upstream full RAG
>   project (657k docs, BM25 + binary vector index, tool-calling agent,
>   human-evaluation site), kept intact as a reference snapshot.
>
> Default branch `dof-icm` has this layout; branch `main` mirrors the upstream
> repository unchanged.

---

## Estructura del repositorio

```
repo (rama dof-icm)
├── dof-icm/        # Workspace nuevo: Q&A portable y file-based (ICM)
├── dof-rag/        # Proyecto legacy: dof-rag upstream (RAG completo)
├── README.md       # Este archivo
├── LICENSE         # MIT (contenido heredado de Codeando Guadalajara)
└── .gitignore      # corpus/, bases, .env, .venv, etc. (no versionados)
```

| Carpeta | Qué es | Para quién | Documentación |
|---|---|---|---|
| `dof-icm/` | **Proyecto nuevo.** Workspace portable sobre el DOF 2024–2026: corpus en markdown, búsqueda por herramientas (grep/lectura), respuestas con citas. Incluye UI web autohospedable con tu propia API key. | Uso diario: preguntas al DOF con cualquier modelo (recomendado: DeepSeek) | [`dof-icm/README.md`](dof-icm/README.md) |
| `dof-rag/` | **Proyecto legacy.** El repositorio upstream completo: pipelines de descarga/conversión, corpus + chunks + índices (BM25/vec0), agente de herramientas y el sitio de evaluación humana (Air + Clerk). | Referencia del proyecto original y de su infraestructura RAG | [`dof-rag/README.md`](dof-rag/README.md) |

---

## dof-icm/ — el proyecto nuevo (recomendado)

Q&A **sin RAG**: no hay embeddings ni base vectorial. El corpus son archivos
`.md` organizados por `YYYY/MM/FECHA/SECCIÓN/`; el agente lee la metodología
[ICM](https://github.com/RinDig/Interpretable-Context-Methodology) (carpetas
como arquitectura, contratos por etapa, skills de recuperación) y responde con
citas exactas (relpath + líneas + fecha + sección).

### Distribución de la carpeta

| Ruta (dentro de `dof-icm/`) | Función |
|---|---|
| `corpus/` | El DOF 2024–2026 en markdown (~52k documentos; se genera con `scripts/setup.sh`, no está versionado). `corpus/index/` tiene los mapas de navegación. |
| `CLAUDE.md`, `CONTEXT.md` | Capas 0–1 de contexto del workspace (mapa y enrutado de tareas). |
| `stages/01-locate/`, `stages/02-verify/` | Contratos de las etapas: localizar candidatos y verificar la respuesta, con `references/` (formato de cita, calidad de respuesta). |
| `skills/dof-retrieval/` | Skill de recuperación (`SKILL.md` + `rules/*.md`). |
| `scripts/` | `run_icm_agent.py` (CLI), `icm_core.py` (núcleo compartido con la UI), `build_corpus.py` + `setup.sh` (construcción del corpus) e `build_indexes.py`. |
| `web/` | **UI web** autohospedable: el flujo de evaluación humana del proyecto legacy adaptado a búsqueda file-based, con tu propia API key (ver `web/README.md`). |
| `eval/` | Set de evaluación (44 preguntas, 7 categorías) + resultados. |
| `setup/` | Cuestionario de arranque (opcional). |

**Uso rápido**

```bash
# 1) corpus (una vez; desde la raíz del repo)
cd dof-rag && uv sync && cd ..        # entorno python legacy (descarga/conversión)
dof-icm/scripts/setup.sh              # construye dof-icm/corpus (~horas)

# 2) UI web con tu propia API key (DeepSeek por defecto)
cd dof-icm
python -m venv web/.venv && web/.venv/bin/pip install -r web/requirements.txt
export DEEPSEEK_API_KEY=sk-... DOF_LOCAL_PASSWORD=...
web/.venv/bin/python -m web.app       # http://127.0.0.1:8765
```

Más detalle en [`dof-icm/README.md`](dof-icm/README.md) y
[`dof-icm/web/README.md`](dof-icm/web/README.md).

---

## dof-rag/ — el proyecto legacy

Snapshot del proyecto upstream **[CodeandoGuadalajara/dof-rag](https://github.com/CodeandoGuadalajara/dof-rag)**:
stack RAG completo sobre el DOF — descarga y conversión a markdown, ~657k
documentos / 6.7M chunks, índice BM25 (FTS5) y vectorial (embeddings binarios
jina-v5 + `sqlite-vec`), agente con herramientas (léxico / vectorial / híbrido)
y el sitio de **evaluación humana** (Air + Clerk) en `human_eval/`.

Se conserva como **referencia** del proyecto original y de dónde salieron las
ideas y el código del que `dof-icm` se deriva:

- `dof-icm/scripts/build_corpus.py` usa el descargador y conversor de
  `dof-rag/` (`get_word_dof.py`, `convert_doc_to_md.py`).
- `dof-icm/web/` es una adaptación file-based de `dof-rag/human_eval/`
  (misma UI, mismo flujo de evaluación; otro motor de respuestas).

Sobre el snapshot se conservan dos parches locales menores: un guard que
rechaza artefactos `.doc` que en realidad son HTML (en `convert_doc_to_md.py`)
y un provider `deepseek` opcional en el executor de `human_eval/`. Todo lo
demás es idéntico al upstream.

Su documentación completa vive en [`dof-rag/README.md`](dof-rag/README.md).

---

## Ramas

| Rama | Contenido |
|---|---|
| `dof-icm` (default) | Estructura de este README: `dof-icm/` + `dof-rag/`. Activa. |
| `main` | Espejo sin cambios del upstream `CodeandoGuadalajara/dof-rag` (para comparar o sincronizar). |

## Licencia

- Contenido heredado del upstream (`dof-rag/`, UI adaptada en `dof-icm/web/`):
  **MIT**, © 2025 Codeando Guadalajara (ver [`LICENSE`](LICENSE)).
- Código nuevo del workspace `dof-icm/`: **MIT**.
- El corpus del DOF es de **dominio público** (publicado por el gobierno
  mexicano); las respuestas del agente son generadas por un modelo de lenguaje
  y no constituyen asesoría legal.
