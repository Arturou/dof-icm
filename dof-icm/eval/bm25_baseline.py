#!/usr/bin/env python3
"""Classic-RAG baseline over the ICM corpus: BM25 (SQLite FTS5) doc retrieval.

Reproduces the lexical retriever of the original dof-rag pipeline (BM25 over
SQLite FTS5, `unicode61 remove_diacritics 1`, MATCH with OR of terms, no
stemming — see dof-rag/dof-rag/reports/retrieval_evaluation.md) but indexes the
ICM corpus (one row per DOF legal document) so it can be compared head-to-head
against the ICM agent on the same corpus and the same gold questions.

No embeddings, no LLM: this measures how well a one-shot classical retriever
surfaces the gold document(s) for each eval question.

Usage:
    # index + query + summarize (first run)
    python eval/bm25_baseline.py --corpus corpus \
        --questions eval/questions_v2.jsonl eval/questions_fiscal.jsonl \
        --db var/bm25_eval.sqlite --out eval/results/bm25_baseline.json

    # query only against an existing index
    python eval/bm25_baseline.py --questions ... --db var/bm25_eval.sqlite \
        --out ... --no-index
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sqlite3
import time
import unicodedata
from pathlib import Path

TOKENIZER = 'unicode61 remove_diacritics 1'
STOPWORDS = {
    "el", "la", "los", "las", "de", "del", "y", "en", "que", "a", "para", "se",
    "con", "por", "al", "un", "una", "unos", "unas", "su", "sus", "es", "son",
    "fue", "era", "como", "mas", "más", "cuál", "cual", "qué", "cuales",
    "cuáles", "cuanto", "cuánto", "cuanta", "cuánta", "cuantos", "cuántos",
    "cuantas", "cuántas", "ser", "está", "esta", "estar", "entre", "sobre",
    "sin", "desde", "hasta", "ante", "bajo", "cada", "este", "esta", "ese",
    "esa", "esto", "eso", "si", "no", "ya", "también", "tambien", "mismo",
    "misma", "puede", "pueden", "debe", "deben", "dice", "dijo", "fue", "han",
    "ha", "he", "haber", "ser", "hace", "hacer", "año", "años", "día", "dia",
    "días", "dias", "mes", "meses", "fecha", "publicado", "publicada",
    "publicación", "publicacion", "diario", "oficial", "federación",
    "federacion", "dof", "según", "segun", "acuerdo", "conforme", "documento",
    "documentos", "artículo", "articulo", "artículos", "articulos", "numeral",
    "fracción", "fraccion", "fracciones", "inciso", "párrafo", "parrafo",
    "numerales", "apartado", "apartados", "título", "titulo", "sección",
    "seccion", "secciones", "capítulo", "capitulo", "capítulos", "capitulos",
    "disposiciones", "transitorios", "transitorio", "vigente", "vigencia",
    "tiene", "tienen", "tener", "contiene", "indica", "establece", "señala",
    "senala", "menciona", "refiere", "respecto", "referente", "relativo",
    "relativa", "relacionado", "relacionada", "pregunta", "respuesta", "caso",
    "casos", "cualquier", "todas", "todos", "toda", "todo", "otra", "otro",
    "otras", "otros", "alguna", "alguno", "algunas", "algunos", "cuáles",
    "cuales", "persona", "personas", "persona física", "fisica", "moral",
}


def norm_token(w: str) -> str:
    s = unicodedata.normalize("NFD", w)
    return "".join(c for c in s if not unicodedata.combining(c)).lower()


def tokens(text: str) -> list[str]:
    words = re.findall(r"[\w]+", unicodedata.normalize("NFC", text), flags=re.UNICODE)
    out = []
    for w in words:
        t = norm_token(w)
        if len(t) < 2 or t in STOPWORDS:
            continue
        out.append(t)
    return out


def fts_query(question: str) -> str:
    ts = tokens(question)
    return " OR ".join(f'"{t}"' for t in ts)


def iter_docs(corpus: Path):
    """Yield (relpath, Path) for every corpus document.

    Corpus layout: <year>/<month>/<DDMMYYYY>/<MAT|VES>/<file>.md
    """
    for f in corpus.rglob("*.md"):
        parts = f.relative_to(corpus).parts
        if len(parts) != 5:
            continue
        year, month, day, section, name = parts
        if not (year.isdigit() and len(year) == 4 and month.isdigit()
                and len(month) == 2 and day.isdigit() and len(day) == 8
                and section in ("MAT", "VES")):
            continue
        yield f.relative_to(corpus).as_posix(), f


def build_index(db_path: Path, corpus: Path) -> int:
    if db_path.exists():
        db_path.unlink()
    con = sqlite3.connect(db_path)
    con.execute(
        f'CREATE VIRTUAL TABLE docs USING fts5(relpath UNINDEXED, body, '
        f'tokenize = "{TOKENIZER}")'
    )
    con.execute("PRAGMA journal_mode=OFF")
    con.execute("PRAGMA synchronous=OFF")
    con.execute("PRAGMA cache_size=-200000")
    n = 0
    t0 = time.time()
    batch = []
    for rel, f in iter_docs(corpus):
        try:
            text = f.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue
        batch.append((rel, text))
        n += 1
        if len(batch) >= 250:
            con.executemany("INSERT INTO docs(relpath, body) VALUES (?, ?)", batch)
            batch = []
            if n % 5000 < 250:
                con.commit()
                el = time.time() - t0
                print(f"indexed {n} docs in {el:.0f}s", flush=True)
    if batch:
        con.executemany("INSERT INTO docs(relpath, body) VALUES (?, ?)", batch)
    con.commit()
    print(f"done: {n} docs in {time.time() - t0:.0f}s", flush=True)
    con.close()
    return n


def query_index(db_path: Path, questions) -> dict:
    con = sqlite3.connect(db_path)
    out = {}
    for q in questions:
        qid = q["id"]
        gold = {d["relpath"] for d in q.get("gold_documents", [])}
        accepted = gold | set(q.get("valid_alternatives", []))
        mq = fts_query(q.get("question", ""))
        if not mq:
            out[qid] = {"rank": None, "top50": [], "any": {}}
            continue
        cur = con.execute(
            "SELECT relpath FROM docs WHERE docs MATCH ? ORDER BY rank LIMIT 200",
            (mq,),
        )
        ranked = [r[0] for r in cur.fetchall()]
        any_gold = {}
        first = None
        for i, rp in enumerate(ranked, start=1):
            if rp in accepted:
                if first is None:
                    first = i
        for k in (1, 5, 10, 20, 50):
            any_gold[str(k)] = any(rp in accepted for rp in ranked[:k])
        out[qid] = {
            "question": q.get("question", "")[:120],
            "n_gold": len(gold),
            "first_gold_rank": first,
            "any_gold_at_k": any_gold,
            "top50_docs": ranked[:50],
        }
    con.close()
    return out


def summarize(per_id: dict, questions, label: str) -> dict:
    by_cat = {}
    for q in questions:
        qid = q["id"]
        agg = by_cat.setdefault(
            q["category"],
            {"n": 0, "any": {str(k): 0 for k in (1, 5, 10, 20, 50)},
             "mrr_sum": 0.0, "hits_at_10": 0},
        )
        r = per_id.get(qid)
        agg["n"] += 1
        if not r:
            continue
        for k in (1, 5, 10, 20, 50):
            if r["any_gold_at_k"].get(str(k)):
                agg["any"][str(k)] += 1
        if r["first_gold_rank"]:
            agg["mrr_sum"] += 1.0 / r["first_gold_rank"]
            if r["first_gold_rank"] <= 10:
                agg["hits_at_10"] += 1
    total = {"n": 0, "any": {str(k): 0 for k in (1, 5, 10, 20, 50)},
             "mrr_sum": 0.0, "hits_at_10": 0}
    for q in questions:
        r = per_id.get(q["id"])
        total["n"] += 1
        if not r:
            continue
        for k in (1, 5, 10, 20, 50):
            if r["any_gold_at_k"].get(str(k)):
                total["any"][str(k)] += 1
        if r["first_gold_rank"]:
            total["mrr_sum"] += 1.0 / r["first_gold_rank"]
            if r["first_gold_rank"] <= 10:
                total["hits_at_10"] += 1
    def fmt(a):
        return {k: f"{v}/{a['n']} ({100.0*v/a['n']:.0f}%)"
                for k, v in a["any"].items()} | \
               {"MRR": round(a["mrr_sum"] / a["n"], 3)}
    return {"label": label, "total": fmt(total),
            "per_category": {c: fmt(a) for c, a in sorted(by_cat.items())}}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", default="corpus")
    ap.add_argument("--questions", nargs="+",
                    default=["eval/questions_v2.jsonl", "eval/questions_fiscal.jsonl"])
    ap.add_argument("--db", default="var/bm25_eval.sqlite")
    ap.add_argument("--out", default="eval/results/bm25_baseline.json")
    ap.add_argument("--no-index", action="store_true",
                    help="skip indexing; reuse an existing db")
    args = ap.parse_args()

    corpus = Path(args.corpus)
    db_path = Path(args.db)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    questions = []
    for qf in args.questions:
        questions += [json.loads(l) for l in
                      Path(qf).read_text(encoding="utf-8").splitlines() if l.strip()]
    print(f"{len(questions)} questions loaded", flush=True)

    if not args.no_index:
        n = build_index(db_path, corpus)
    else:
        con = sqlite3.connect(db_path)
        n = con.execute("SELECT count(*) FROM docs").fetchone()[0]
        con.close()
        print(f"reusing index with {n} docs", flush=True)

    t0 = time.time()
    per_id = query_index(db_path, questions)
    print(f"queries done in {time.time() - t0:.0f}s", flush=True)

    result = {
        "method": "BM25 (SQLite FTS5, unicode61 remove_diacritics 1, OR terms, "
                  "no stemming) — one row per DOF document",
        "corpus": str(corpus),
        "indexed_docs": n,
        "per_question": per_id,
        "summaries": [
            summarize(per_id, [q for q in questions if "FS-" in q["id"]],
                      "fiscal (12)"),
            summarize(per_id, [q for q in questions if "FS-" not in q["id"]],
                      "general v2 (44)"),
            summarize(per_id, questions, "all (56)"),
        ],
    }
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(result, ensure_ascii=False, indent=1))
    print(json.dumps(result["summaries"], ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
