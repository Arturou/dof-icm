#!/usr/bin/env bash
# DOF-ICM one-shot setup: download + convert + index + cleanup.
# Runs from the parent dof-rag/ checkout (needs uv, soffice, pandoc).
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ICM="$REPO_ROOT/dof-icm"
CORPUS="$ICM/corpus"
START="${1:-01/01/2024}"
END="${2:-31/12/2026}"

echo "==> Downloading DOF .doc files ($START → $END) into dof_word/"
cd "$REPO_ROOT"
uv run get_word_dof.py "$START" "$END" --editions both --sleep-delay 0.2

echo "==> Converting .doc → .md into $CORPUS"
mkdir -p "$CORPUS"
uv run python convert_doc_to_md.py --input-dir ./dof_word --output-dir "$CORPUS" --workers 4

echo "==> Building navigation indexes"
cd "$ICM"
python scripts/build_indexes.py --corpus "$CORPUS"

echo "==> Deleting .doc files (verified conversion complete)"
rm -rf "$REPO_ROOT/dof_word"

echo "==> Done. Corpus: $(find "$CORPUS" -name '*.md' | wc -l) markdown files"
