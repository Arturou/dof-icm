#!/usr/bin/env python3
"""Build DOF-ICM navigation index files from the corpus.

Scans dof-icm/corpus/ (YYYY/MM/DD/SECTION/file.md) and writes:

    corpus/index/by-year-YYYY.md     one file per year
    corpus/index/by-section-MAT.md   MAT docs grouped by year
    corpus/index/by-section-VES.md   VES docs grouped by year
    corpus/index/recent.md           last N days of docs

Usage:
    python scripts/build_indexes.py [--corpus dof-icm/corpus] [--recent-days 30]
"""

from __future__ import annotations

import argparse
import datetime as dt
import re
from collections import defaultdict
from pathlib import Path

DOC_RE = re.compile(
    r"^(?P<year>\d{4})/(?P<month>\d{2})/(?P<day>\d{8})/(?P<section>[A-Z]+)/"
    r"(?P<name>.+\.md)$"
)


def extract_title(text: str, max_len: int = 90) -> str:
    """Best-effort title from markdown: first heading or bold block."""
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith("#"):
            return line.lstrip("# ").strip()[:max_len]
        if line.startswith("**") and line.endswith("**"):
            return line.strip("*").strip()[:max_len]
    return ""


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", default="dof-icm/corpus", type=Path)
    ap.add_argument("--recent-days", default=30, type=int)
    args = ap.parse_args()

    corpus: Path = args.corpus
    if not corpus.exists():
        raise SystemExit(f"corpus not found: {corpus} (run download + convert first)")

    years: dict[int, dict[str, list[tuple[dt.date, Path]]]] = defaultdict(
        lambda: defaultdict(list)
    )
    sections: dict[str, dict[int, int]] = defaultdict(lambda: defaultdict(int))
    all_docs: list[tuple[dt.date, Path]] = []

    for path in sorted(corpus.rglob("*.md")):
        rel = path.relative_to(corpus).as_posix()
        m = DOC_RE.match(rel)
        if not m:
            continue
        year = int(m.group("year"))
        section = m.group("section")
        day8 = m.group("day")  # DDMMYYYY
        date = dt.date(year, int(day8[2:4]), int(day8[0:2]))
        years[year][section].append((date, path))
        sections[section][year] += 1
        all_docs.append((date, path))

    index_dir = corpus / "index"
    index_dir.mkdir(parents=True, exist_ok=True)

    for year in sorted(years):
        out = index_dir / f"by-year-{year}.md"
        lines = [f"# DOF documents published in {year}", ""]
        total = 0
        # Per-month counts (fast scoping without reading 20k lines)
        month_counts: dict[int, int] = defaultdict(int)
        for section in sorted(years[year]):
            docs = sorted(years[year][section])
            total += len(docs)
            for date, _p in docs:
                month_counts[date.month] += 1
            lines.append(f"## Section {section} — {len(docs)} documents")
            lines.append("")
            # Sample: first 5 + last 5 titles
            samples = docs[:5] + (docs[-5:] if len(docs) > 10 else [])
            seen: set[tuple] = set()
            for date, path in samples:
                key = (date, path.name)
                if key in seen:
                    continue
                seen.add(key)
                title = extract_title(path.read_text(errors="replace")[:4000])
                lines.append(
                    f"- {date.isoformat()} `{path.relative_to(corpus).as_posix()}`"
                    + (f" — {title}" if title else "")
                )
            lines.append("")
        # Doc counts by month (insert after header line + blank)
        month_lines = ["", "## Documents per month", ""]
        month_lines.append("| Month | Documents |")
        month_lines.append("|-------|-----------|")
        for m in range(1, 13):
            if month_counts.get(m):
                month_lines.append(f"| {m:02d} | {month_counts[m]} |")
        month_lines.append("")
        lines = lines[:1] + [f"**Total: {total} documents**"] + month_lines + lines[1:]
        out.write_text("\n".join(lines) + "\n")
        print(f"wrote {out} ({total} docs)")

        # Full title index: one line per doc — relpath<TAB>title.
        # Lets the agent locate docs by title with a single fast grep
        # instead of scanning the whole corpus.
        title_out = index_dir / f"titles-{year}.md"
        tlines: list[str] = []
        for section in sorted(years[year]):
            for date, path in sorted(years[year][section]):
                title = extract_title(path.read_text(errors="replace")[:4000])
                tlines.append(
                    f"{path.relative_to(corpus).as_posix()}\t{title or '(sin título)'}"
                )
        title_out.write_text("\n".join(tlines) + "\n")
        print(f"wrote {title_out} ({len(tlines)} titles)")

    for section in sorted(sections):
        out = index_dir / f"by-section-{section}.md"
        lines = [
            f"# DOF section {section} — all years",
            "",
            "| Year | Documents |",
            "|------|-----------|",
        ]
        for year in sorted(sections[section]):
            lines.append(f"| {year} | {sections[section][year]} |")
        out.write_text("\n".join(lines) + "\n")
        print(f"wrote {out}")

    cutoff = dt.date.today() - dt.timedelta(days=args.recent_days)
    recent = [d for d in all_docs if d[0] >= cutoff]
    recent.sort(key=lambda x: x[0], reverse=True)
    out = index_dir / "recent.md"
    lines = [
        f"# Recent DOF documents (last {args.recent_days} days, since {cutoff.isoformat()})",
        "",
        f"**{len(recent)} documents**",
        "",
    ]
    for date, path in recent[:200]:
        lines.append(f"- {date.isoformat()} `{path.relative_to(corpus).as_posix()}`")
    if len(recent) > 200:
        lines.append("")
        lines.append(f"*…and {len(recent) - 200} more*")
    out.write_text("\n".join(lines) + "\n")
    print(f"wrote {out} ({len(recent)} recent docs)")


if __name__ == "__main__":
    main()
