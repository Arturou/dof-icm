#!/usr/bin/env bash
# DOF-ICM: one-shot retry over quarantined .doc files.
# Runs convert_doc_to_md.py with input=quarantine, output=corpus.
# After conversion, deletes quarantined .doc whose .md now exists;
# persistent failures STAY in quarantine for manual inspection.
set -uo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
QUAR="$REPO_ROOT/dof-icm/dof_failed/quarantine"
CORPUS="$REPO_ROOT/dof-icm/corpus"
WORKERS="${1:-4}"

if [ ! -d "$QUAR" ]; then
  echo "no quarantine dir ($QUAR)"
  exit 0
fi

n="$(find "$QUAR" -name '*.doc' | wc -l | tr -d ' ')"
echo "==> Retrying $n quarantined docs (workers=$WORKERS)"
cd "$REPO_ROOT"
uv run python convert_doc_to_md.py \
  --input-dir "$QUAR" --output-dir "$CORPUS" --workers "$WORKERS" \
  >> /tmp/dof_retry.log 2>&1

deleted=0; still=0
while IFS= read -r doc; do
  rel="${doc#$QUAR/}"
  md="$CORPUS/${rel%.doc}.md"
  if [ -s "$md" ]; then
    rm -f "$doc"; deleted=$((deleted + 1))
  else
    still=$((still + 1))
  fi
done < <(find "$QUAR" -name '*.doc')
echo "==> Retry pass done: recovered=$deleted still-failed=$still"
find "$QUAR" -type d -empty -delete 2>/dev/null || true
