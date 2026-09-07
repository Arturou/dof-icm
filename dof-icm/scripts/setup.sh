#!/usr/bin/env bash
# DOF-ICM one-shot setup: download + convert + cleanup + index.
#
# Builds the corpus to the SAME quality as the reference build:
#   - converts .doc -> .md (parallel; HTML-junk .doc artifacts skipped fast)
#   - quarantines HTML error pages saved as .doc (never convertible)
#   - retries real failures (e.g. 14-68 MB decrees) with a long timeout
#   - deletes each .doc ONLY after its .md is verified non-empty
#   - builds navigation indexes (by-year / titles / by-section / recent)
#
# Requirements (macOS): uv, LibreOffice (soffice), pandoc
#   brew install libreoffice pandoc
#   mise install && uv sync        # python deps (from repo root)
#
# Usage (from the dof-rag repo root):
#   dof-icm/scripts/setup.sh                      # full 2024-2026 build
#   dof-icm/scripts/setup.sh 01/01/2025 31/12/2025  # narrower range
#   dof-icm/scripts/setup.sh --no-download        # convert existing dof_word/
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$REPO_ROOT"

echo "==> DOF-ICM corpus builder (uv, soffice, pandoc required)"
uv run python dof-icm/scripts/build_corpus.py "$@"
