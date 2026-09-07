#!/usr/bin/env bash
# DOF-ICM one-shot setup: download + convert + cleanup + index.
#
# Builds the corpus to the SAME quality as the reference build:
#   - downloads DOF .doc (2024-2026) with the legacy dof-rag get_word_dof.py
#   - converts .doc -> .md (parallel; HTML-junk .doc artifacts skipped fast)
#   - quarantines HTML error pages saved as .doc (never convertible)
#   - retries real failures (e.g. 14-68 MB decrees) with a long timeout
#   - deletes each .doc ONLY after its .md is verified non-empty
#   - builds navigation indexes (by-year / titles / by-section / recent)
#
# Requirements (macOS): uv, LibreOffice (soffice), pandoc
#   brew install libreoffice pandoc
#   cd dof-rag && uv sync     # python env for the legacy downloader/converter
#
# Usage (from the repo root, i.e. the folder containing dof-icm/ and dof-rag/):
#   dof-icm/scripts/setup.sh                      # full 2024-2026 build
#   dof-icm/scripts/setup.sh 01/01/2025 31/12/2025  # narrower range
#   dof-icm/scripts/setup.sh --no-download        # convert existing dof_word/
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$REPO_ROOT"

echo "==> DOF-ICM corpus builder (uv, soffice, pandoc required)"
echo "==> using legacy env dof-rag/ (get_word_dof.py + convert_doc_to_md.py)"
uv run --project "$REPO_ROOT/dof-rag" python dof-icm/scripts/build_corpus.py "$@"
