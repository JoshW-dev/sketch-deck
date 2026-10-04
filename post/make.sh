#!/bin/zsh
# Post-production for a recorded sketch-deck video. See post/README.md.
#
#   post/make.sh prep   "<recording>.take" "<NN slug>" ["terms for Whisper"]
#   (review the list it prints, add hand cuts to work/edl.json "manual")
#   post/make.sh finish "<NN slug>" "<Title>"
#
# Everything lands in ~/Movies/Josh Wade AI/<NN slug>/.
set -e
HERE=${0:A:h}
ROOT=${SKETCH_POST_OUT:-$HOME/Movies/Josh Wade AI}
PY=${SKETCH_POST_ENV:-$HOME/.cache/sketch-deck-post}/venv-audio/bin/python
WHISPER=(uv run --quiet --python 3.11 --with mlx-whisper --with soundfile python)

case $1 in
  prep)
    TAKE=${2:A}; WORK="$ROOT/$3/work"; mkdir -p "$WORK"
    echo "1/4 export at 1440p and 2/4 voice, in parallel (about 4 min)"
    python3 "$HERE/export.py" "$TAKE" "$WORK" > "$WORK/export.log" 2>&1 &
    "$PY" "$HERE/voice.py" "$TAKE" "$WORK" > "$WORK/voice.log" 2>&1 &
    wait
    tail -1 "$WORK/export.log"; tail -1 "$WORK/voice.log"
    echo "3/4 transcribe"
    $WHISPER "$HERE/transcribe.py" "$WORK" "${4:-}" 2>&1 | grep -v Fetching
    echo "4/4 find cuts"
    $WHISPER "$HERE/cuts.py" "$WORK" 2>&1 | grep -v Fetching
    ;;
  finish)
    WORK="$ROOT/$2/work"
    "$PY" "$HERE/render.py" "$WORK" "$3"
    "$PY" "$HERE/review.py" "$WORK" "$3"
    ;;
  *)
    sed -n '2,9p' "$0"; exit 1 ;;
esac
