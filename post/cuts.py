"""Step 4. Propose the edit: confirmed "um"s and the still part of long pauses are cut automatically.
Restarts and repeated phrases are only listed, because they need a person to choose which take
stays. Add those by hand to the "manual" list in edl.json, then render.

Usage: uv run --quiet --python 3.11 --with mlx-whisper --with soundfile python post/cuts.py <workdir>
Writes <workdir>/edl.json and <workdir>/motion.npy. Keeps any "manual" cuts already in edl.json."""
import json
import re
import subprocess
import sys
from pathlib import Path

import mlx_whisper
import numpy as np
import soundfile as sf

sys.path.insert(0, str(Path(__file__).parent))
from common import FPS, WHISPER, load, mmss, words  # noqa: E402

work = Path(sys.argv[1]).expanduser()
y, sr = sf.read(work / "voice.wav", dtype="float32")
y = y.mean(1) if y.ndim > 1 else y
R = 200  # envelope steps per second
hop = sr // R
env = 20 * np.log10(np.sqrt((y[:len(y) // hop * hop].reshape(-1, hop) ** 2).mean(1)) + 1e-9)
speech = np.percentile(env, 90)
w = words(work / "words-disfluent.json")


def level(a, b):
    return env[int(a * R):max(int(a * R) + 1, int(b * R))].max() - speech


# screen motion per frame, with the camera bubble masked out
motion_file = work / "motion.npy"
if not motion_file.exists():
    proj = load(work / "export.take/project.json")
    ew, eh = load(work / "frame.json")["export"]
    sw, sh = ew // 10, eh // 10
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(work / "video.mp4"), "-vf", f"scale={sw}:{sh},format=gray",
                          "-f", "rawvideo", "-"], capture_output=True, check=True).stdout
    f = np.frombuffer(raw, np.uint8).reshape(-1, sh, sw).astype(np.int16)
    b = proj["bubble"]
    bh = b["size"] * sh * 1.15
    bw = bh if b["shape"] == "circle" else bh * 16 / 9
    m = b["margin"] * sh
    x0 = sw - m - bw if "Right" in b["corner"] else m - 2
    y0 = sh - m - bh if b["corner"].startswith("bottom") else m - 2
    mask = np.ones((sh, sw), bool)
    mask[max(0, int(y0)):int(y0 + bh + 4), max(0, int(x0)):int(x0 + bw + 4)] = False
    mot = np.concatenate([[0], ((np.abs(np.diff(f, axis=0)) > 6) & mask).sum((1, 2))])
    np.save(motion_file, mot)
mot = np.load(motion_file)


def still(a, b):
    return not mot[max(0, int(a * FPS) - 3):int(b * FPS) + 4].any()


# voiced segments, bridging gaps under 40 ms
voiced = env > speech - 28
segs, i = [], 0
while i < len(voiced):
    if voiced[i]:
        j = i
        while j < len(voiced) and (voiced[j] or voiced[j:j + 8].any()):
            j += 1
        segs.append((i / R, j / R))
        i = j
    else:
        i += 1


def heard(a, b):
    sf.write(work / "piece.wav", y[int(a * sr):int(b * sr)], sr)
    return mlx_whisper.transcribe(str(work / "piece.wav"), path_or_hf_repo=WHISPER, language="en",
                                  initial_prompt="Umm, uh, um, hmm.", temperature=0)["text"].strip()


cuts = []
# 1. "um" and "uh" that stand alone. Whisper's word times run up to 200 ms late, so the cut comes
#    from the envelope: the filler is its own voiced segment, confirmed by transcribing it alone.
for k, x in enumerate(w[1:-1], 1):
    if x["word"].strip(" ,.").lower() not in ("um", "uh", "umm", "uhm"):
        continue
    hits = []
    nxt = w[k + 1]["start"]
    for n, (s, e) in enumerate(segs):
        if s < nxt + 0.1 and e > x["start"] - 0.3 and 0.12 <= e - s <= 0.9 and 0 < n < len(segs) - 1:
            t = heard(max(0, s - 0.08), e + 0.08)
            if re.fullmatch(r"(?i)\W*(u+h*m+|u+h+|hmm+|m+)\W*", t):
                hits.append((n, s, e))
    if len(hits) != 1:
        continue
    n, s, e = hits[0]
    before, after = s - segs[n - 1][1], segs[n + 1][0] - e
    if before < 0.1 or after < 0.05:
        continue  # runs into a word
    cuts.append({"start": round(s - 0.02, 3), "end": round(max(e + 0.01, segs[n + 1][0] - max(0.05, 0.3 - before)), 3),
                 "kind": "um", "label": "um"})

# 2. the still middle of pauses over 1 s: keep 0.35 s after the last word and 0.25 s before the next.
#    Pauses come from the envelope, because Whisper's word times move between runs.
for (_, g0), (g1, _) in zip(segs, segs[1:]):
    if g1 - g0 <= 1.0:
        continue
    run = None
    for fr in range(int((g0 + 0.35) * FPS), int((g1 - 0.25) * FPS) + 1):
        ok = fr < int((g1 - 0.25) * FPS) and still(fr / FPS, fr / FPS)
        if ok and run is None:
            run = fr
        if not ok and run is not None:
            a, b = run / FPS, fr / FPS
            if b - a >= 0.2 and level(a, b) < -25:
                cuts.append({"start": round(a, 3), "end": round(b, 3), "kind": "pause", "label": "pause trimmed"})
            run = None

cuts.sort(key=lambda c: c["start"])
merged = []
for c in cuts:
    if merged and c["start"] <= merged[-1]["end"] + 0.05:
        merged[-1]["end"] = max(merged[-1]["end"], c["end"])
    else:
        merged.append(c)
old = load(work / "edl.json") if (work / "edl.json").exists() else {}
edl = {"auto": merged, "manual": old.get("manual", [])}
json.dump(edl, open(work / "edl.json", "w"), indent=1)
print(f"auto: {sum(c['kind'] == 'um' for c in merged)} um, {sum(c['kind'] == 'pause' for c in merged)} pauses, "
      f"{sum(c['end'] - c['start'] for c in merged):.1f} s. manual: {len(edl['manual'])}")

# 3. for a person to judge: long silences (often a restart) and phrases said twice
print("\nReview these. Add a cut to edl.json 'manual' as "
      '{"start": s, "end": e, "kind": "double take", "label": "..."} for each one to remove.')
for p, q in zip(w, w[1:]):
    if q["start"] - p["end"] > 4:
        print(f"  silence {mmss(p['end'])} to {mmss(q['start'])} ({q['start'] - p['end']:.1f} s) after '{p['word'].strip()}'")
toks = [(re.sub(r"[^a-z0-9']", "", x["word"].lower()), x) for x in w]
toks = [t for t in toks if t[0] and t[0] not in ("um", "uh")]
seen = set()
for n in range(8, 3, -1):
    for i in range(len(toks) - n):
        if i in seen:
            continue
        a = [t[0] for t in toks[i:i + n]]
        for j in range(i + n, len(toks) - n + 1):
            if toks[j][1]["start"] - toks[i][1]["start"] > 4:
                break
            if [t[0] for t in toks[j:j + n]] == a:
                print(f"  said twice ({n} words) at {mmss(toks[i][1]['start'])} and {mmss(toks[j][1]['start'])}: {' '.join(a)}")
                seen.update(range(i, i + n))
                break
for n in (2, 1):
    for i in range(len(toks) - 2 * n + 1):
        a, b = [t[0] for t in toks[i:i + n]], [t[0] for t in toks[i + n:i + 2 * n]]
        if a == b and i not in seen and toks[i + n][1]["start"] - toks[i + n - 1][1]["end"] < 0.4 and not (n == 1 and a[0] in ("very", "really", "no", "that")):
            print(f"  stutter at {mmss(toks[i][1]['start'])}: {' '.join(a)}, {' '.join(b)}")
            seen.update(range(i, i + 2 * n))
