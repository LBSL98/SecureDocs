#!/usr/bin/env bash
set -euo pipefail

ROOT="${1:-audit_reports}"

if [ ! -d "$ROOT" ]; then
  echo "001"
  exit 0
fi

MAX_NUM="$(
  find "$ROOT" -type f -printf '%f\n' 2>/dev/null \
    | sed -n 's/^\([0-9][0-9][0-9]\)_.*/\1/p' \
    | sort -n \
    | tail -n 1
)"

if [ -z "${MAX_NUM:-}" ]; then
  echo "001"
else
  printf "%03d\n" "$((10#$MAX_NUM + 1))"
fi
