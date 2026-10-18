"""Step 5. Render the upload file from Take's 1440p export and the mastered voice, applying every cut
in edl.json in one encode, then write captions and list chapter points.

Usage: ~/.cache/sketch-deck-post/venv-audio/bin/python post/render.py <workdir> "<Title>"
Writes "<workdir>/../<Title> (final).mp4" and ".srt", <workdir>/final-words.json, cuts-final.json and keep.json."""
import json
import subprocess
import sys
import textwrap
from pathlib import Path

import numpy as np
import soundfile as sf

sys.path.insert(0, str(Path(__file__).parent))
from common import FPS, SR, load, mmss, run, save  # noqa: E402

work, title = Path(sys.argv[1]).expanduser(), sys.argv[2]
out = work.parent / f"{title} (final).mp4"
crop = load(work / "frame.json")["crop"]
edl = load(work / "edl.json")
voice, _ = sf.read(work / "voice.wav", dtype="float32")
dur = len(voice) / SR
# Hand-picked cuts come from transcript times, which can be 100 ms off. Move each edge to the
# quietest 10 ms within 80 ms, so it lands in silence.
hop = SR // 100
venv = 20 * np.log10(np.sqrt((voice[:len(voice) // hop * hop].reshape(-1, hop) ** 2).mean(1)) + 1e-9)


def snap(t):
    i0, i1 = max(0, int((t - 0.08) * 100)), int((t + 0.08) * 100)
    return (i0 + int(np.argmin(venv[i0:i1 + 1]))) / 100


manual = [{**c, "start": snap(c["start"]), "end": snap(c["end"])} for c in edl["manual"]]
cuts = sorted(edl["auto"] + manual, key=lambda c: c["start"])

keep, t = [], 0.0
for c in cuts:
    if c["start"] > t:
        keep.append((t, c["start"]))
    t = max(t, c["end"])
keep.append((t, dur))
save(work / "keep.json", keep)  # the export-timeline pieces of the final cut, for shorts.py

# Video and audio are joined separately: one joint concat pads the audio to each piece's video
# length and drifts (+31 ms by the end on video 01). Each video piece starts on the source frame
# that lines up with where its audio lands, so picture and sound stay within half a frame.
lines, frames, samples, worst = [], 0, 0, 0.0
crop_f = f"crop={crop['w']}:{crop['h']}:{crop['x']}:{crop['y']}"
for i, (a, b) in enumerate(keep):
    s0, s1 = round(a * SR), round(b * SR)
    f0 = round(a * FPS + frames - samples / SR * FPS)
    worst = max(worst, abs((f0 / FPS - a) - (frames / FPS - samples / SR)))
    samples += s1 - s0
    nf = round(samples / SR * FPS) - frames
    frames += nf
    d = (s1 - s0) / SR
    lines.append(f"[0:v]trim=start_frame={f0}:end_frame={f0 + nf},setpts=PTS-STARTPTS,{crop_f}[v{i}];")
    lines.append(f"[1:a]atrim=start_sample={s0}:end_sample={s1},asetpts=PTS-STARTPTS,"
                 f"afade=t=in:d=0.005,afade=t=out:st={max(0, d - 0.005):.4f}:d=0.005[a{i}];")
lines.append("".join(f"[v{i}]" for i in range(len(keep))) + f"concat=n={len(keep)}:v=1:a=0[v];")
lines.append("".join(f"[a{i}]" for i in range(len(keep))) + f"concat=n={len(keep)}:v=0:a=1[a]")
(work / "render.filter").write_text("\n".join(lines))
run("ffmpeg", "-v", "error", "-stats", "-y", "-i", work / "video.mp4", "-i", work / "voice.wav",
    "-filter_complex_script", work / "render.filter", "-map", "[v]", "-map", "[a]",
    "-c:v", "libx264", "-preset", "slow", "-crf", "17", "-pix_fmt", "yuv420p", "-r", FPS,
    "-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709",
    "-c:a", "aac", "-b:a", "320k", "-ar", SR, "-ac", "2", "-movflags", "+faststart", out)


def to_final(t):
    return t - sum(min(c["end"], t) - c["start"] for c in cuts if c["start"] < t)


# captions from the clean transcript. It usually has no "um"s or stutters, so only words inside
# a removed take longer than half a second are dropped.
def removed(t):
    return any(c["start"] <= t < c["end"] for c in cuts if c["kind"] == "double take" and c["end"] - c["start"] > 0.5)


segs = []
for s in load(work / "words.json")["segments"]:
    ws = [{**x, "start": to_final(x["start"]), "end": to_final(x["end"])} for x in s["words"]
          if not removed((x["start"] + x["end"]) / 2)]
    if ws:
        segs.append({"words": ws, "text": "".join(x["word"] for x in ws)})
save(work / "final-words.json", {"segments": segs, "text": "".join(s["text"] for s in segs)})
words = [x for s in segs for x in s["words"]]


def ts(t):
    ms = int(round(t * 1000))
    return f"{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}"


cues, cur = [], []
for i, x in enumerate(words):
    cur.append(x)
    text = "".join(c["word"] for c in cur).strip()
    nxt = words[i + 1] if i + 1 < len(words) else None
    if (nxt is None or (text[-1:] in ".?!" and cur[-1]["end"] - cur[0]["start"] > 1.0) or len(text + nxt["word"]) > 80
            or nxt["start"] - x["end"] > 0.8 or x["end"] - cur[0]["start"] > 6):
        cues.append((cur[0]["start"], x["end"], text))
        cur = []
with open(out.with_suffix(".srt"), "w") as f:
    for n, (a, b, text) in enumerate(cues, 1):
        rows = textwrap.wrap(text, 42) if len(text) > 42 else [text]
        if len(rows) > 2:
            rows = textwrap.wrap(text, (len(text) + 1) // 2 + 4)
        f.write(f"{n}\n{ts(a)} --> {ts(max(b, a + 0.8))}\n" + "\n".join(rows) + "\n\n")

save(work / "cuts-final.json", [{**c, "at": round(to_final(c["start"]), 2), "length": round(c["end"] - c["start"], 2)} for c in cuts])

# checks: duration, loudness, and sound against the voice track with the same cuts
ref = np.concatenate([voice[round(a * SR):round(b * SR)] for a, b in keep])
got = subprocess.run(["ffmpeg", "-v", "error", "-i", str(out), "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"],
                     capture_output=True, check=True).stdout
got = np.frombuffer(got, np.float32)


def env(x):
    k = SR // 1000
    return np.sqrt((x[:len(x) // k * k].reshape(-1, k) ** 2).mean(1))


er, eg = env(ref), env(got)
offsets = []
for t0 in range(10, int(len(er) / 1000) - 12, 40):
    a = er[t0 * 1000:(t0 + 8) * 1000]
    b = eg[t0 * 1000 - 300:(t0 + 8) * 1000 + 300]
    a = (a - a.mean()) / (a.std() + 1e-9)
    offsets.append(int(np.argmax(np.correlate(b - b.mean(), a, "valid")) - 300))
loud = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(out), "-af", "ebur128=peak=true", "-f", "null", "-"],
                      capture_output=True, text=True).stderr
loud = " ".join(line.strip() for line in loud[loud.rfind("Summary"):].splitlines() if line.strip().startswith(("I:", "Peak:")))
print(f"\n{out.name}: {mmss(samples / SR)}, {len(cuts)} cuts ({dur - samples / SR:.1f} s removed), {loud}")
print(f"sound offset every 40 s (ms): {offsets}; worst picture offset at a cut {worst * 1000:.0f} ms; {len(cues)} captions")

# chapter points: the deck's board view is grey (#f1f3f5) and slides are white
raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(out), "-vf", "fps=4,crop=2:2:300:40,format=gray", "-f", "rawvideo", "-"],
                     capture_output=True, check=True).stdout[::4]
print("\nChapter points (the board closes and a part opens):")
print("  0:00")
last = -10.0
for i in range(2, len(raw)):
    # board for at least half a second, then a slide that stays up for a second
    if raw[i - 2] < 248 and raw[i - 1] < 248 <= raw[i] and (i + 4 >= len(raw) or raw[i + 4] >= 248) and i / 4 - last > 5:
        t = last = i / 4
        nxt = [x for x in words if x["start"] >= t - 0.5][:12]
        print(f"  {int(t // 60)}:{int(t % 60):02d}  {''.join(x['word'] for x in nxt).strip()}")
