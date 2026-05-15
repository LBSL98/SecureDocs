#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -lt 3 ]; then
  echo "Uso: $0 <subpasta_em_audit_reports> <slug> <script_temporario.sh>" >&2
  exit 1
fi

SUBDIR="$1"
SLUG="$2"
SCRIPT_FILE="$3"

ROOT="audit_reports"
NEXT_ID="$(scripts/next_audit_id.sh "$ROOT")"
OUTDIR="$ROOT/$SUBDIR"
OUTFILE="$OUTDIR/${NEXT_ID}_${SLUG}.txt"

mkdir -p "$OUTDIR"

echo "AUDIT_OUTFILE=$OUTFILE"
/usr/bin/time -v bash -x "$SCRIPT_FILE" 2>&1 | tee "$OUTFILE"
