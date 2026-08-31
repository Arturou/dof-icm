#!/usr/bin/env bash
# DOF-ICM incremental converter: runs alongside the downloader.
#
# Strategy (race-free):
#   1. Detect the downloader's current (year, month) from its log.
#   2. `mv` completed months (strictly before current month) from
#      dof_word/  ->  dof_staging/  (downloader never revisits them).
#   3. Run convert_doc_to_md.py over dof_staging (preserves
#      YYYY/MM/DD/SECTION output structure under dof-icm/corpus/).
#   4. Verify every .md output exists + non-empty, then delete the
#      staging .doc files (and empty dirs) to free disk.
#   5. Sleep, repeat.
#
# Usage:  scripts/convert_parallel.sh [logfile] [interval_sec] [workers]
set -uo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
WORD="$REPO_ROOT/dof_word"
STAGE="$REPO_ROOT/dof_staging"
CORPUS="$REPO_ROOT/dof-icm/corpus"
LOG="${1:-/tmp/dof_download.log}"
INTERVAL="${2:-120}"
WORKERS="${3:-4}"

mkdir -p "$STAGE" "$CORPUS"

echo "==> Incremental converter started (interval ${INTERVAL}s, workers ${WORKERS})"

while true; do
  # --- 1. downloader position ---
  line="$(grep "Processing page" "$LOG" 2>/dev/null | tail -1 || true)"
  cur_year="$(echo "$line" | grep -oE 'year=[0-9]{4}' | head -1 | cut -d= -f2 || true)"
  cur_month="$(echo "$line" | grep -oE 'month=[0-9]{2}' | head -1 | cut -d= -f2 || true)"
  if [ -z "${cur_year:-}" ] || [ -z "${cur_month:-}" ]; then
    echo "[$(date +%T)] downloader log has no position yet; sleeping"
    sleep "$INTERVAL"
    continue
  fi

  # --- 2. move completed months ---
  moved=0
  for year_dir in "$WORD"/20*/; do
    [ -d "$year_dir" ] || continue
    year="$(basename "$year_dir")"
    for month_dir in "$year_dir"*/; do
      [ -d "$month_dir" ] || continue
      month="$(basename "$month_dir")"
      # month is complete iff (year,month) < (cur_year,cur_month)
      if [ "$year" -lt "$cur_year" ] || { [ "$year" -eq "$cur_year" ] && [ "$month" -lt "$cur_month" ]; }; then
        n_doc="$(find "$month_dir" -name '*.doc' | wc -l | tr -d ' ')"
        [ "$n_doc" -gt 0 ] || continue
        mkdir -p "$STAGE/$year"
        mv "$month_dir" "$STAGE/$year/"
        echo "[$(date +%T)] staged $year/$month ($n_doc docs)"
        moved=$((moved + 1))
      fi
    done
  done

  # --- 3. convert staging ---
  years="$(ls "$STAGE" 2>/dev/null | tr '\n' ' ' | sed 's/ *$//')"
  if [ -n "$years" ]; then
    echo "[$(date +%T)] converting staged years: $years"
    cd "$REPO_ROOT"
    uv run python convert_doc_to_md.py \
      --input-dir "$STAGE" --years $years \
      --output-dir "$CORPUS" --workers "$WORKERS" \
      >> /tmp/dof_convert.log 2>&1
  fi

  # --- 3b. quarantine docs the converter just marked failed ---
  # (they burn 90s*3 retries every pass; move them out so the loop
  #  stops re-attempting them; keep the .doc for manual inspection)
  FAILED_LIST="$REPO_ROOT/dof-icm/dof_failed/failed_files.txt"
  if [ -f "$FAILED_LIST" ]; then
    QUAR="$REPO_ROOT/dof-icm/dof_failed/quarantine"
    while IFS= read -r bad; do
      if [ -f "$bad" ] && [[ "$bad" == "$STAGE/"* ]]; then
        rel="${bad#$STAGE/}"
        mkdir -p "$QUAR/$(dirname "$rel")"
        mv "$bad" "$QUAR/$rel"
        echo "[$(date +%T)] quarantined: $rel" >> /tmp/dof_convert.log
      fi
    done < "$FAILED_LIST"
    rm -f "$FAILED_LIST"
  fi

  # --- 4. verify + delete staged .doc files ---
  deleted=0; missing=0
  while IFS= read -r doc; do
    rel="${doc#$STAGE/}"
    md="$CORPUS/${rel%.doc}.md"
    if [ -s "$md" ]; then
      rm -f "$doc"
      deleted=$((deleted + 1))
    else
      missing=$((missing + 1))
      echo "[$(date +%T)] MISSING OUTPUT for: $doc" >> /tmp/dof_convert.log
    fi
  done < <(find "$STAGE" -name '*.doc' 2>/dev/null)
  if [ "$deleted" -gt 0 ] || [ "$missing" -gt 0 ]; then
    echo "[$(date +%T)] cleaned: deleted=$deleted missing=$missing"
  fi
  # prune empty staging dirs
  find "$STAGE" -type d -empty -delete 2>/dev/null || true

  # --- done? ---
  if [ "$moved" -eq 0 ] && [ "$deleted" -eq 0 ] && [ -z "$years" ]; then
    # check downloader still alive
    if ! pgrep -f "get_word_dof.py" >/dev/null 2>&1; then
      echo "[$(date +%T)] downloader finished; converter exiting"
      break
    fi
  fi
  sleep "$INTERVAL"
done
echo "==> Incremental converter done"
