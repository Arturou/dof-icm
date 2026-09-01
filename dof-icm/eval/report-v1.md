# DOF-ICM Evaluation Report — DeepSeek v4-flash (optimized)

**Date:** 2026-09-01
**Config:** `deepseek-v4-flash` @ `https://api.deepseek.com/v1`, `reasoning_effort=minimal`, `MAX_TURNS=8`, `search_titles` tool, whole-file reads, efficiency rules.
**Set:** `eval/questions.jsonl` — 28 questions, 7 categories, gold docs 2024–2026.
**Results:** `eval/results/run_deepseek_v4_flash.jsonl`

## Summary

| Metric | Value |
|---|---|
| Questions run | 28/28 |
| Completed (final answer) | 20/28 (71%) |
| Capped at MAX_TURNS=8 | 8/28 (29%) |
| **Doc-level hit (cited gold relpath)** | **19/28 = 68%** |
| Doc-level hit, completed only | 19/20 = 95% |
| Total tool calls | 261 (avg 9.3/q) |
| Total tokens | 1,053,345 in / 49,383 out |

## Per-category doc-hit

| Category | Hit | Why |
|---|---|---|
| single_passage | 3/3 | 100% — easiest |
| list_enumeration | 5/5 | 100% |
| cross_reference | 3/4 | 75% |
| monitoring | 3/4 | 75% |
| temporal_transitorio | 2/4 | 50% (2 capped) |
| multi_document | 1/3 | 33% (2 capped) |
| negative_false_premise | 2/5 | 40% (3 capped) |

## Analysis

**19/20 completed answers cite the correct gold document (95%).** The 8 caps are concentrated in the hard categories (temporal, multi-doc, negative-premise): those questions need 2–3 gold docs or long reads (e.g. TE-004's 1,900-line law), and 8 turns is too tight for them — several had found the right docs and were mid-read when capped.

**CR-003** completed but missed gold (cited 2024 VES docs instead of the Tren Maya decree) — a genuine retrieval error.

## Cost estimate

~1M input tokens total ≈ $0.27 @ $0.27/M (deepseek-v4-flash pricing varies) — cost is minor; the constraint is wall-clock (reasoning turns).

## Next options

1. **Re-run the 8 capped + 1 missed** with `MAX_TURNS=14` (targeted salvage, ~30-40 min).
2. Ship as-is: 68% doc-hit, 95% precision-on-completed is a solid first baseline.
3. Improve retrieval for negative-premise questions (they need explicit "premise false" handling in stage-02 contract).
