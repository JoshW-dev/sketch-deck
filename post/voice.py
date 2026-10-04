"""Step 2. Rebuild the voice from the raw camera mic: MelBand-Roformer dereverb, then Sidon voice
restoration, then a light master to -14 LUFS. Take's own Clean voice is skipped on purpose: its
compressor lifts the room echo (SRMR 3.83 against 5.39 for the raw mic on video 01).

Usage: ~/.cache/sketch-deck-post/venv-audio/bin/python post/voice.py "<recording>.take" <workdir>
Writes <workdir>/raw.wav (raw mic on the export timeline) and <workdir>/voice.wav (mastered)."""
import json
import re
import subprocess
import sys
from pathlib import Path

import numpy as np
import soundfile as sf
from scipy.signal import resample_poly

sys.path.insert(0, str(Path(__file__).parent))
from common import DEREVERB_MODEL, SEPARATOR, SEPARATOR_MODELS, SR, kept_ranges, run  # noqa: E402

bundle, work = Path(sys.argv[1]).expanduser(), Path(sys.argv[2]).expanduser()
project = json.load(open(bundle / "project.json"))
cam = bundle / project["camera"]["fileName"]

# 1. raw mic, cut to the same timeline as Take's export
ranges = kept_ranges(project)
graph = "".join(f"[0:a]atrim={a}:{b},asetpts=PTS-STARTPTS[a{i}];" for i, (a, b) in enumerate(ranges))
graph += "".join(f"[a{i}]" for i in range(len(ranges))) + f"concat=n={len(ranges)}:v=0:a=1,aresample={SR}[out]"
run("ffmpeg", "-v", "error", "-y", "-i", cam, "-filter_complex", graph, "-map", "[out]", "-ac", "1", "-c:a", "pcm_f32le", work / "raw.wav")
x, sr = sf.read(work / "raw.wav", dtype="float32")
x = x * (0.7 / max(1e-6, np.abs(x).max()))  # the laptop mic records around -40 LUFS
sf.write(work / "raw-norm.wav", x, sr, subtype="FLOAT")

# 2. dereverb
sep = work / "separator"
run(SEPARATOR, work / "raw-norm.wav", "-m", DEREVERB_MODEL, "--model_file_dir", SEPARATOR_MODELS, "--output_dir", sep,
    "--output_format", "WAV", stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
dry = next(p for p in sep.iterdir() if p.name.startswith("raw-norm_(noreverb)"))
y, ysr = sf.read(dry, dtype="float32")
y = y.mean(1) if y.ndim > 1 else y

# 3. Sidon, in chunks under its 10 s window. `speech restore` drops ~20 ms per window, so a whole
#    file drifts out of sync (0.6 s by 5 minutes). Chunks are cut in pauses found in the envelope,
#    carry 0.5 s of context each side, and crossfade over 40 ms.
hop = ysr // 100
env = 20 * np.log10(np.sqrt((y[:len(y) // hop * hop].reshape(-1, hop) ** 2).mean(1)) + 1e-9)
quiet = env < np.percentile(env, 90) - 30
gaps, i = [], 0
while i < len(quiet):
    if quiet[i]:
        j = i
        while j < len(quiet) and quiet[j]:
            j += 1
        gaps.append(((i + j) / 200, (j - i) / 100))
        i = j
    else:
        i += 1
dur = len(y) / ysr
cuts, start = [0.0], 0.0
while dur - start > 8.5:
    window = [(t, g) for t, g in gaps if start + 3 < t <= start + 8.5]
    long = [t for t, g in window if g >= 0.12]
    start = max(long) if long else (max(window, key=lambda p: p[1])[0] if window else start + 8.5)
    cuts.append(start)
cuts.append(dur)
chunks = work / "chunks"
chunks.mkdir(exist_ok=True)
out = np.zeros(int(dur * SR) + SR, dtype=np.float32)
PAD, XF = 0.5, 0.04
for k, (a, b) in enumerate(zip(cuts, cuts[1:])):
    a0, b0 = max(0, a - PAD), min(dur, b + PAD)
    ci, co = chunks / f"{k:03d}.wav", chunks / f"{k:03d}-out.wav"
    sf.write(ci, y[int(a0 * ysr):int(b0 * ysr)], ysr, subtype="FLOAT")
    run("speech", "restore", ci, "-o", co, capture_output=True)
    c, csr = sf.read(co, dtype="float32")
    if csr != SR:
        c = resample_poly(c, SR, csr).astype(np.float32)
    t = a0 + np.arange(len(c)) / SR
    g = np.clip((t - (a - XF / 2)) / XF, 0, 1) if a > 0 else np.ones(len(c))
    if b < dur:
        g = g * np.clip(((b + XF / 2) - t) / XF, 0, 1)
    p = int(round(a0 * SR))
    n = min(len(c), len(out) - p)
    out[p:p + n] += (c * g)[:n]
sf.write(work / "restored.wav", out[:int(round(dur * SR))], SR, subtype="FLOAT")
print(f"Sidon: {len(cuts) - 1} chunks")

# 4. master: high-pass, gentle compression, de-esser, two-pass loudness to -14 LUFS / -1.5 dBTP
pre = "highpass=f=70,acompressor=threshold=-22dB:ratio=2.5:attack=8:release=150:makeup=2,deesser=i=0.25"
log = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(work / "restored.wav"), "-af",
                      f"{pre},loudnorm=I=-14:TP=-1.5:LRA=9:print_format=json", "-f", "null", "-"],
                     capture_output=True, text=True).stderr
m = json.loads(re.search(r"\{[^{}]*\}", log[log.rfind("{") - 1:], re.S).group(0))
measured = (f"measured_I={m['input_i']}:measured_TP={m['input_tp']}:measured_LRA={m['input_lra']}:"
            f"measured_thresh={m['input_thresh']}:offset={m['target_offset']}")
run("ffmpeg", "-v", "error", "-y", "-i", work / "restored.wav", "-af",
    f"{pre},loudnorm=I=-14:TP=-1.5:LRA=9:{measured}:linear=true,aresample={SR}", "-c:a", "pcm_s24le", work / "voice.wav")
print(f"wrote {work / 'voice.wav'}")
