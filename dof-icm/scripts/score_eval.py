#!/usr/bin/env python3
"""Score ICM eval runs against gold docs, with ambiguity handling.

Reads the eval questions JSONL + a run results JSONL, computes:
  - completion rate
  - doc-level hit (cited relpath in gold set) — with `ambiguity` handling:
      * `multiple_valid`: any of `gold_documents` OR `valid_alternatives`
        relpaths counts as a hit (CR-003-style: several decrees share
        identical article text).
      * otherwise: strict gold-set match.
  - semantic answer match (loose: key figures from reference_answer present
    in the model answer, case-insensitive on a few alnum tokens)
  - per-category and per-difficulty breakdowns
  - cost/token stats

Usage:
    python scripts/score_eval.py --questions eval/questions.jsonl \
        --results eval/results/RUN.jsonl --tag "deepseek-v4-flash"
"""

from __future__ import annotations

import argparse
import json
import re
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

REL_RE = re.compile(r"20\d\d/\d\d/\d{8}/(?:MAT|VES)/[A-Za-z0-9_\-]+\.md")


def norm(s: str) -> str:
    s = unicodedata.normalize("NFD", s).lower()
    return "".join(c for c in s if not unicodedata.combining(c))


def key_figures(reference: str) -> set[str]:
    """Digits, percents, and currency amounts in the reference answer."""
    figs = set()
    for tok in re.findall(r"[\d][\d.,]*|\d+(?:\.\d+)?\s*%|\$\s*[\d][\d.,]*", reference):
        t = tok.replace(" ", "")
        figs.add(norm(t))
    # also whole words that are mostly digits/amount markers
    return {f for f in figs if f}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--questions", default="eval/questions.jsonl")
    ap.add_argument("--results", required=True)
    ap.add_argument("--tag", default="run")
    args = ap.parse_args()

    questions = [json.loads(l) for l in Path(args.questions).read_text().splitlines() if l.strip()]
    q_by_id = {q["id"]: q for q in questions}

    runs: dict[str, dict] = {}
    for line in Path(args.results).read_text().splitlines():
        if line.strip():
            r = json.loads(line)
            runs[r["id"]] = r  # last wins (later retry overrides)

    rows = []
    for q in questions:
        r = runs.get(q["id"])
        if r is None:
            continue
        status = r.get("stop_reason") or r.get("error", "?")
        completed = status == "completed"
        answer = r.get("answer") or ""
        cited = set(REL_RE.findall(answer))
        # ambiguity-aware gold set
        gold = {d["relpath"] for d in q.get("gold_documents", [])}
        alternatives = set(q.get("valid_alternatives", []))
        accepted = gold | alternatives
        hit = bool(cited & accepted) if completed else False
        # semantic check on key figures
        ref = q.get("reference_answer") or ""
        figs = key_figures(ref)
        an = norm(answer)
        sem = bool(figs) and all(f in an for f in figs)
        rows.append(
            {
                "id": q["id"],
                "category": q.get("category", "?"),
                "difficulty": q.get("difficulty", "?"),
                "ambiguity": q.get("ambiguity", "none"),
                "status": status,
                "completed": completed,
                "hit": hit,
                "semantic": sem and completed,
                "tools": len(r.get("trace", [])),
                "gold": sorted(gold),
                "cited": sorted(cited),
            }
        )

    n = len(rows)
    done = sum(1 for x in rows if x["completed"])
    hits = sum(1 for x in rows if x["hit"])
    sem = sum(1 for x in rows if x["semantic"])
    tools = [x["tools"] for x in rows]
    print(f"=== {args.tag}: {n} questions ===")
    print(f"completed: {done}/{n} ({done/n:.0%})")
    print(f"doc-hit (ambiguity-aware): {hits}/{n} ({hits/n:.0%})   [{hits}/{done} of completed]")
    print(f"semantic (key figures in answer): {sem}/{n} ({sem/n:.0%})")
    if tools:
        print(f"tools: avg {sum(tools)/len(tools):.1f}  min {min(tools)}  max {max(tools)}")
    print()
    by_cat = defaultdict(lambda: [0, 0, 0, 0])
    for x in rows:
        c = by_cat[x["category"]]
        c[0] += 1
        c[1] += x["hit"]
        c[2] += x["semantic"]
        c[3] += x["completed"]
    print("per category (n / hit / semantic / completed):")
    for cat in sorted(by_cat):
        n_, h, s, d = by_cat[cat]
        print(f"  {cat:24s} {n_:2d}  {h:2d}  {s:2d}  {d:2d}")
    print()
    print("misses (completed but no hit):")
    for x in rows:
        if x["completed"] and not x["hit"]:
            print(f"  {x['id']} [{x['category']}/{x['difficulty']}/{x['ambiguity']}] cited={x['cited'][:1]} gold={x['gold'][:1]}")


if __name__ == "__main__":
    main()
