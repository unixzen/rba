#!/bin/bash
# Transcribe one batch of images via pi agent.
# Usage: transcribe.sh <batch-id, e.g. n00>
# Model can be overridden: PI_PROVIDER=... PI_MODEL=... transcribe.sh n00
set -u
BATCH="$1"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PROVIDER="${PI_PROVIDER:-litellm}"
MODEL="${PI_MODEL:-mimo-v2.6-pro}"

BATCHFILE="$ROOT/data/batches/$BATCH.json"
OUTFILE="$ROOT/data/out/$BATCH.txt"
[ -f "$BATCHFILE" ] || { echo "no batch file: $BATCHFILE" >&2; exit 1; }

PROMPT="$(sed -e "s|BATCHFILE|$BATCHFILE|g" \
              -e "s|IMGDIR|$ROOT/img|g" \
              -e "s|OUTFILE|$OUTFILE|g" \
              "$ROOT/scripts/transcribe_template.txt")"

exec pi --provider "$PROVIDER" --model "$MODEL" -p "$PROMPT" --no-session -n "transcribe-$BATCH"
