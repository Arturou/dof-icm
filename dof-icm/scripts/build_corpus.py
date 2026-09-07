#!/usr/bin/env python3
"""Build the DOF-ICM corpus to the same quality as the reference build.

Reproduces the local pipeline exactly:
  1. (optional) download DOF .doc files via the upstream get_word_dof.py
  2. convert .doc -> .md with the repo converter (HTML-junk guard built in),
     in a parallel pass (workers)
  3. quarantine HTML error pages saved as .doc (never convertible) into
     <output_dir>/../dof_failed/html/ and DELETE them (they are junk)
  4. retry REAL remaining failures with a long LibreOffice timeout
     (some DOF .doc are 14-68 MB and exceed the default 90 s)
  5. verify every .md exists + non-empty BEFORE deleting its .doc
     (never delete a failed document silently)
  6. build navigation indexes (by-year / titles / by-section / recent)
  7. report counts

Usage (from the repo root that contains pyproject.toml, after `uv sync`):
    uv run python dof-icm/scripts/build_corpus.py \
        [--start 01/01/2024] [--end 31/12/2026] [--workers 4] [--no-download]
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import time
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
ICM = REPO_ROOT / "dof-icm"
CORPUS = ICM / "corpus"
WORD_DIR = REPO_ROOT / "dof_word"
FAILED_ROOT = ICM / "dof_failed"
HTML_JUNK = FAILED_ROOT / "html"
RETAINED = FAILED_ROOT / "retained_failures"

sys.path.insert(0, str(REPO_ROOT))

RETRY_LO_TIMEOUT = 1200  # seconds, for large .doc files
RETRY_PANDOC_TIMEOUT = 1800


def log(msg: str) -> None:
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


def detect_html(doc: Path) -> bool:
    """A .doc that is really an HTML error page (downloader artifact)."""
    try:
        with open(doc, "rb") as f:
            head = f.read(2048)
    except OSError:
        return False
    lhead = head.lstrip().lower()
    return lhead.startswith(b"<!doctype") or lhead.startswith(b"<html")


def convert_pass(files: list[Path], workers: int) -> dict:
    """Parallel .doc->.md pass using the repo converter (resumable)."""
    import convert_doc_to_md as conv

    conv.INPUT_DIR = WORD_DIR  # so get_output_path maps full YYYY/MM/... tree
    conv.OUTPUT_DIR = CORPUS
    out: dict = {"ok": 0, "failed": [], "skipped": 0}
    work = []
    for doc in files:
        out_md = conv.get_output_path(doc)
        if out_md.exists() and out_md.stat().st_size > 0:
            out["skipped"] += 1
            continue
        work.append((doc, out_md))
    if not work:
        return out
    with ProcessPoolExecutor(max_workers=workers) as ex:
        futs = {ex.submit(conv.convert_single_doc, d, m, i % workers): d for i, (d, m) in enumerate(work)}
        for fut in as_completed(futs):
            doc = futs[fut]
            r = fut.result()
            if r["status"] == "success":
                out["ok"] += 1
            else:
                out["failed"].append(doc)
    return out


def retry_failures(failed: list[Path]) -> tuple[list[Path], list[Path]]:
    """Retry real failures sequentially with a long LO timeout."""
    import convert_doc_to_md as conv

    conv.INPUT_DIR = WORD_DIR
    conv.OUTPUT_DIR = CORPUS
    conv.LIBREOFFICE_TIMEOUT = RETRY_LO_TIMEOUT
    conv.PANDOC_TIMEOUT = RETRY_PANDOC_TIMEOUT
    recovered: list[Path] = []
    still_bad: list[Path] = []
    for doc in failed:
        out_md = conv.get_output_path(doc)
        r = conv.convert_single_doc(doc, out_md, worker_id=99)
        if r["status"] == "success":
            recovered.append(doc)
            log(f"  recovered (long timeout): {doc.relative_to(WORD_DIR)}")
        else:
            still_bad.append(doc)
    return recovered, still_bad


def download_docs(start: str, end: str) -> None:
    log(f"Downloading DOF .doc files {start} -> {end} (this can take hours)")
    cmd = [
        sys.executable, "get_word_dof.py", start, end,
        "--editions", "both", "--sleep-delay", "0.2",
    ]
    subprocess.run(cmd, cwd=REPO_ROOT, check=True)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--start", default="01/01/2024")
    ap.add_argument("--end", default="31/12/2026")
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--no-download", action="store_true",
                    help="skip download; use existing dof_word/ .doc files")
    args = ap.parse_args()

    # Sanity: deps of the upstream pipeline present
    if not (REPO_ROOT / "pyproject.toml").exists():
        sys.exit(f"run from the repo root containing pyproject.toml (found {REPO_ROOT})")
    for exe in ("soffice", "pandoc"):
        if not shutil.which(exe):
            sys.exit(f"missing required executable: {exe} (brew install libreoffice pandoc)")

    WORD_DIR.mkdir(parents=True, exist_ok=True)
    if not args.no_download:
        download_docs(args.start, args.end)
    elif not any(WORD_DIR.rglob("*.doc")):
        sys.exit("no .doc files found in dof_word/ and --no-download given")

    docs = sorted(WORD_DIR.rglob("*.doc"))
    log(f"documents to convert: {len(docs)}")

    # Pass 1: parallel convert (converter has the HTML-junk fast guard)
    r1 = convert_pass(docs, args.workers)
    log(f"pass 1: {r1['ok']} ok, {len(r1['failed'])} failed, {r1['skipped']} skipped")
    remaining = [d for d in docs if not (CORPUS / d.relative_to(WORD_DIR)).with_suffix(".md").exists()]

    # Separate HTML junk from real failures
    html_junk = [d for d in remaining if detect_html(d)]
    real_failed = [d for d in remaining if not detect_html(d)]
    log(f"html junk .doc artifacts: {len(html_junk)} (deleted — never convertible)")
    for d in html_junk:
        rel = d.relative_to(WORD_DIR)
        dst = HTML_JUNK / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        try:
            d.replace(dst)  # keep a copy in dof_failed/html for inspection
        except OSError:
            d.unlink()

    # Retry real failures with the long timeout (big 14-68 MB docs)
    if real_failed:
        log(f"retrying {len(real_failed)} real failures with {RETRY_LO_TIMEOUT}s timeout...")
        recovered, still_bad = retry_failures(real_failed)
        log(f"  retry recovered: {len(recovered)}, still failing: {len(still_bad)}")
        for d in still_bad:
            rel = d.relative_to(WORD_DIR)
            dst = RETAINED / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            try:
                d.replace(dst)
            except OSError:
                pass
    else:
        still_bad = []

    # Verify-then-delete: only remove .doc whose .md exists and is non-empty
    deleted, missing = 0, 0
    for d in sorted(WORD_DIR.rglob("*.doc")):
        md = (CORPUS / d.relative_to(WORD_DIR)).with_suffix(".md")
        if md.exists() and md.stat().st_size > 0:
            d.unlink()
            deleted += 1
        else:
            missing += 1
            log(f"  WARN no .md for {d.relative_to(WORD_DIR)} — keeping .doc")
    log(f"cleanup: deleted {deleted} .doc (verified), kept {missing} unverified")

    # Indexes (by-year / titles / by-section / recent) — same builder as the
    # reference corpus.
    log("building navigation indexes...")
    idx_script = Path(__file__).parent / "build_indexes.py"
    subprocess.run(
        [sys.executable, str(idx_script), "--corpus", str(CORPUS)],
        check=True,
    )

    n_md = sum(1 for _ in CORPUS.rglob("*.md"))
    print("=" * 60)
    print(f"DONE. corpus: {n_md} markdown files in {CORPUS}")
    if html_junk:
        print(f"  HTML junk moved to: {HTML_JUNK}")
    if still_bad:
        print(f"  real failures kept for manual inspection: {RETAINED}")
    print(f"  indexes: {CORPUS/'index'}")
    print("=" * 60)


if __name__ == "__main__":
    main()
