"""Shared helpers for the post-production scripts. Times are seconds on the Take export timeline
(the source after Take's own trim and cuts) unless a name says otherwise."""
import json
import os
import subprocess
from pathlib import Path

ENV = Path(os.environ.get("SKETCH_POST_ENV", Path.home() / ".cache/sketch-deck-post"))
AUDIO_PY = ENV / "venv-audio/bin/python"
SEPARATOR = ENV / "venv-sep/bin/audio-separator"
SEPARATOR_MODELS = ENV / "models/separator"
DEREVERB_MODEL = "dereverb_mel_band_roformer_mono_anvuew.ckpt"
WHISPER = "mlx-community/whisper-large-v3-turbo"
FPS, SR = 30, 48000


def run(*cmd, **kw):
    return subprocess.run([str(c) for c in cmd], check=True, **kw)


def load(path):
    return json.load(open(path))


def save(path, data):
    json.dump(data, open(path, "w"), indent=1)


def kept_ranges(project):
    """Same rule as TakeProject.keptRanges: the parts of the source that survive trim and cuts."""
    end = project.get("trimEnd") or 0
    end = min(end, project["duration"]) if end > 0 else project["duration"]
    ranges, cursor = [], project.get("trimStart", 0)
    for cut in sorted(project.get("cuts", []), key=lambda c: c["start"]):
        start, stop = max(cut["start"], cursor), min(cut["end"], end)
        if start > cursor:
            ranges.append((cursor, start))
        if stop > cursor:
            cursor = stop
    if end > cursor:
        ranges.append((cursor, end))
    return [r for r in ranges if r[1] - r[0] > 0.001]


def words(path):
    return [w for s in load(path)["segments"] for w in s["words"]]


def mmss(t):
    t = round(t, 2)
    return f"{int(t // 60)}:{t % 60:05.2f}"
