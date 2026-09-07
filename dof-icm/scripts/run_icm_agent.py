#!/usr/bin/env python3
"""Run the DOF-ICM two-stage agent against an OpenAI-compatible API.

Thin CLI over ``icm_core`` (see that module for the agent logic). The core is
shared with the web UI executor, so CLI eval runs and UI runs behave alike.

Usage:
    DEEPSEEK_API_KEY=... python scripts/run_icm_agent.py \
        --question "¿Cuál es el salario mínimo general para 2026?"
    python scripts/run_icm_agent.py --eval-json eval/questions.jsonl --ids SP-001
    python scripts/run_icm_agent.py --eval-json eval/questions.jsonl --all
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

try:
    from openai import OpenAI
except ImportError:  # pragma: no cover
    OpenAI = None

import icm_core

WORKSPACE = Path(__file__).resolve().parent.parent


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--question", help="Single question to answer")
    ap.add_argument("--eval-json", help="Path to eval/questions.jsonl")
    ap.add_argument("--ids", help="Comma-separated question ids (subset)")
    ap.add_argument("--all", action="store_true", help="All questions in eval set")
    ap.add_argument("--model", default="deepseek-v4-flash")
    ap.add_argument("--base-url", default="https://api.deepseek.com/v1")
    ap.add_argument("--max-tokens", type=int, default=None,
                    help="max_tokens per completion (needed for LM Studio/Qwen; None = API default)")
    ap.add_argument("--out", default=str(WORKSPACE / "eval/results/run.jsonl"))
    args = ap.parse_args()

    api_key = os.environ.get("DEEPSEEK_API_KEY") or os.environ.get("OPENAI_API_KEY") or "local"
    if OpenAI is None:
        sys.exit("openai package not installed (uv sync)")

    client = OpenAI(api_key=api_key, base_url=args.base_url)
    questions: list[dict] = []
    if args.question:
        questions = [{"id": "manual", "question": args.question}]
    elif args.eval_json:
        with open(args.eval_json) as f:
            questions = [json.loads(line) for line in f if line.strip()]
        if args.ids:
            ids = {i.strip() for i in args.ids.split(",")}
            questions = [q for q in questions if q["id"] in ids]
        elif not args.all:
            by_cat: dict[str, dict] = {}
            for q in questions:
                by_cat.setdefault(q["category"], q)
            questions = list(by_cat.values())  # one per category (7)
    else:
        sys.exit("provide --question or --eval-json")

    results = []
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    for q in questions:
        print(f"==> {q['id']}: {q['question'][:80]}", flush=True)
        # inject question metadata (as-of date, required hops, category) so
        # the agent anchors its search in time instead of wandering years.
        bits = []
        if q.get("as_of"):
            bits.append(f'Reference date ("as of"): {q["as_of"]}')
        if q.get("required_hops"):
            bits.append(f"Required hops (documents): {q['required_hops']}")
        if q.get("category"):
            bits.append(f"Category: {q['category']}")
        meta = ("\n".join(f"6b. {b}" for b in bits)) if bits else ""
        r = icm_core.run_question(
            client, args.model, q["question"], q["id"],
            q.get("category", ""), meta,
            max_tokens=args.max_tokens,
        )
        results.append(r)
        with open(out_path, "a") as f:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
        print(f"    stop={r.get('stop_reason')} tools={len(r.get('trace', []))}", flush=True)
        if r.get("answer"):
            print(f"    answer: {r['answer'][:200].replace(chr(10), ' ')}", flush=True)

    print(f"\nWrote {len(results)} results to {out_path}")


if __name__ == "__main__":
    main()
