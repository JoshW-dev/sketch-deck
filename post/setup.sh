#!/bin/zsh
# One-time setup for post/ on a new Mac (Apple Silicon). Needs Homebrew, uv and ffmpeg.
# Environments go in ~/.cache/sketch-deck-post (about 4 GB with models).
set -e
ENV=${SKETCH_POST_ENV:-$HOME/.cache/sketch-deck-post}
mkdir -p "$ENV/models/separator"
command -v speech >/dev/null || brew install speech          # Sidon voice restoration (soniqo speech-swift)
[ -x "$ENV/venv-audio/bin/python" ] || { uv venv -q --python 3.11 "$ENV/venv-audio"; VIRTUAL_ENV="$ENV/venv-audio" uv pip install -q numpy scipy soundfile; }
[ -x "$ENV/venv-sep/bin/audio-separator" ] || { uv venv -q --python 3.11 "$ENV/venv-sep"; VIRTUAL_ENV="$ENV/venv-sep" uv pip install -q "audio-separator[cpu]"; }
# Whisper (mlx-whisper) runs through `uv run --with mlx-whisper` and downloads its model on first use.
echo "ready: $ENV"
