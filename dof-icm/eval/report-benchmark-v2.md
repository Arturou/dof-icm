# DOF-ICM Benchmark — DeepSeek v4-flash vs Qwen 3.8-27b

**Date:** 2026-09-01
**Eval set:** `eval/questions_v2.jsonl` — 44 questions, 7 categories, gold docs 2024–2026.
**Scoring:** `scripts/score_eval.py` (ambiguity-aware doc-hit; semantic = key figures from reference answer present in the model answer).
**Results:** `eval/results/bench_deepseek.jsonl`, `eval/results/bench_qwen.jsonl` (partial — see caveat).

## Summary

| Metric | **DeepSeek v4-flash** (hosted API) | **Qwen 3.8-27b** (LM Studio, NVIDIA 4090) |
|---|---|---|
| Questions | 44/44 | 24/44 ⚠️ partial |
| Doc-hit (ambiguity-aware) | **40/44 = 91%** | 20/24 = 83% (partial) |
| Completed | 42/44 (95%) | 23/24 (96%) |
| Semantic (key figures) | 21/44 (48%) | 7/24 (29%) |
| Avg tool calls / question | 6.0 | 7.1 |
| Context window | API default (large) | 32.5k (LM Studio), compaction @75% |
| Runtime | ~45 min for 44 | ~2 h for 24 (then machine crashed) |

## DeepSeek per-category (44Q)

| Category | n | hit | completed |
|---|---|---|---|
| list_enumeration | 7 | 7 | 7 |
| monitoring | 6 | 6 | 6 |
| multi_document | 5 | 5 | 5 |
| temporal_transitorio | 6 | 6 | 6 |
| single_passage | 7 | 6 | 6 |
| negative_false_premise | 7 | 6 | 7 |
| cross_reference | 6 | 4 | 5 |

DeepSeek misses (4): CR-003 (ambiguity — valid alternate decree), NE-006 (near-identical Apr 17/20 decrees), 2 not-completed.

## Qwen misses (partial, 4)

- SP-005, LI-003: cited 2026-04-20 decree, gold is 2026-04-17 (near-identical Tren Maya expropriation decrees — same ambiguity family as CR-003).
- LI-004: wrong doc (2026 PND? vs 2025 PND gold).
- 1 not-completed.

## Caveats

1. **Qwen result is partial (24/44)** — the 4090 box (heavymetal-poet, LM Studio) crashed twice during the run (context overflow before compaction landed; then a second crash mid-run). Local-model testing was **skipped** per operator decision. 20/24 on the completed subset is *not* comparable head-to-head with DeepSeek's 44/44.
2. Semantic metric undercounts: reference answers and model answers phrase figures differently ("$315.04" vs "315.04 pesos"). Doc-hit is the primary metric.
3. Qwen needed: user-turn seed (jinja template), explicit `--max-tokens`, higher turn cap (`DOF_MAX_TURNS=14`), and the new context compaction.

## Infrastructure learnings (local LLM)

- **Context compaction** (committed `fda3ed9`): token-budget tracking + digest-based mid-conversation compaction. Verified correct on DeepSeek (7 compactions, answer intact). On Qwen the compacted run reached ~15-18k tokens/turn without overflow before the 2nd crash — but the 32.5k window + 4090 is fragile for this multi-hop tool loop.
- DeepSeek thinking-mode validation rejects a standalone digest assistant message before a tool-call turn — digest must be merged into the retained assistant content (`reasoning_content` must be echoed back).

## Verdict

DeepSeek v4-flash is the **practical choice** for this harness today: 91% doc-hit on 44 questions in ~45 min with zero infra risk. Qwen 3.8-27b on a 32.5k/4090 window is workable for short single-hop questions but unreliable for the full eval (context pressure + crashes); it would need a larger context window or a smaller/quantized model to be a dependable local fallback.
