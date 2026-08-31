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

## Scoring (ICM-style, no chunks)

The upstream v4 set scores chunk-level recall. ICM has no chunks — the retrieval unit is the **document**. Score each run on:

1. **Doc-level hit (R@k):** does the agent's located candidate set (stage 01 output) contain the gold `relpath`? Check top-1, top-5, top-10.
2. **Answer correctness:** does the final answer (stage 02 output) contain the reference answer's key figures/dates, with a correct citation?
3. **Citation precision:** is the cited relpath actually one of the gold docs (or a defensible equivalent)?

Run logs land in `eval/results/[timestamp]-[model]-run.md`, one per question.

## How to run

Point the agent at this workspace with the recommended model config, and run each question through the two stages. Script a harness loop if your agent framework supports it; otherwise run interactively.

Suggested smoke set (1 per category): SP-001, LI-002, TE-003, CR-005, MD-002, MO-005, NE-005.

## Baselines

- Upstream dof-rag v4 (full RAG, BM25+vectors, hybrid): MRR 0.339 / all-hop@20 0.595 (from `dof-rag/reports/eval_v4_retrieval.md`).
- Compare apples-to-apples only on the 28 in-range questions; the upstream numbers are over all 42.

## Extending

- Hand-pick more 2024–2026 questions (Option A), or regenerate a proper v5 with the v3/v4 methodology constrained to 2024–2026 gold docs (Option B, later).
