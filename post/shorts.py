"""Step 8. Vertical shorts (1080x1920) cut from the finished video: the slide on top, Josh's camera in
the bottom third, a hook line played first, burned-in captions, and a card with the hook text that
stays up for the whole short.

Usage: ~/.cache/sketch-deck-post/venv-audio/bin/python post/shorts.py <workdir> [n]
With no shorts.json yet, it only writes <workdir>/shorts-transcript.txt to pick from. With one, it
renders every short (or just short n) into <workdir>/../shorts/: "<n> <slug>.mp4", a contact sheet
"<n> <slug>.jpg" and shorts.md. Needs keep.json and final-words.json from render.py.

shorts.json (times are on the final video's timeline, in seconds or "m:ss.s"):
  {"shorts": [{"slug": "mixer", "title": "post title", "card": "Would you buy a *$100 mixer*?",
               "hook": ["2:41.0", "2:44.2"], "body": [["1:56.0", "3:06.0"]], "why": "..."}]}
"hook" plays first, then each "body" span in order. A hook can also be a list of spans, to drop a
filler word inside it. Each edge moves to the quietest 10 ms nearby, and an "=" before a time
("=5:06.45") keeps that edge exactly where it is. *stars* in the card mark words drawn in orange.
Optional per short or top level: "face": [cx, cy, width] in camera pixels, to place the face crop."""
import json
import shutil
import subprocess
import sys
import textwrap
from pathlib import Path

import numpy as np
import soundfile as sf
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0, str(Path(__file__).parent))
from common import FPS, SR, kept_ranges, load, mmss, run  # noqa: E402

FONTS = Path(__file__).parent / "fonts"
W, H, CAM_H = 1080, 1920, 640       # camera fills the bottom third
TOP = H - CAM_H                     # card, slide and captions share the top 1280 px
CARD_H, CAP_H = 300, 230            # card band at the top, caption band above the camera
BG, INK, ACCENT = (252, 252, 252), (24, 24, 24), (232, 137, 44)   # the deck's paper, ink and orange
CANVAS_W, CONTENT_RIGHT = 1920, 1560   # deck.js: content stays left of x 1540 on a 1920 canvas
MIN_LEN, MAX_LEN, HOOK_MAX = 30, 180, 4.5
# Lay everything out in RGB. Overlaying the screen's YUV on a YUV page shifted the slide's white by
# 3 levels on video 01, which drew a visible box around the slide.
RGB_IN = "in_color_matrix=bt709:in_range=tv"

work = Path(sys.argv[1]).expanduser()
only = int(sys.argv[2]) if len(sys.argv) > 2 else None
take = work / "export.take"
project = load(take / "project.json")
screen_file, camera_file = take / project["screen"]["fileName"], take / project["camera"]["fileName"]
mirror = project.get("bubble", {}).get("mirrored", False)
keep = load(work / "keep.json")
segments = load(work / "final-words.json")["segments"]
words = [{**w, "word": w["word"].strip()} for s in segments for w in s["words"] if w["word"].strip()]


def sec(x):
    if isinstance(x, str):
        x = x.lstrip("=")
        m, s = x.split(":") if ":" in x else ("0", x)
        return int(m) * 60 + float(s)
    return float(x)


# 1. A sentence-per-line transcript on the final timeline, which is what the picker reads.
lines, cur = [], []
for i, w in enumerate(words):
    cur.append(w)
    nxt = words[i + 1] if i + 1 < len(words) else None
    if nxt is None or w["word"][-1:] in ".?!" or nxt["start"] - w["end"] > 1.2:
        lines.append(f"[{mmss(cur[0]['start'])} - {mmss(cur[-1]['end'])}] " + " ".join(x["word"] for x in cur))
        cur = []
(work / "shorts-transcript.txt").write_text("\n".join(lines) + "\n")
spec_file = work / "shorts.json"
if not spec_file.exists():
    print(f"wrote {work / 'shorts-transcript.txt'} ({len(lines)} sentences). Pick the shorts into {spec_file}, "
          "see post/README.md \"Shorts\", then run this again.")
    sys.exit(0)
spec = load(spec_file)

voice, sr = sf.read(work / "voice.wav", dtype="float32")
assert sr == SR, f"voice.wav is {sr} Hz, expected {SR}"
voice = voice.mean(1) if voice.ndim > 1 else voice
hop = SR // 100
venv = 20 * np.log10(np.sqrt((voice[:len(voice) // hop * hop].reshape(-1, hop) ** 2).mean(1)) + 1e-9)

# Timelines: final (the upload) <- keep.json <- export (voice.wav) <- kept_ranges <- source (Take's files)
fin0 = np.cumsum([0.0] + [b - a for a, b in keep])
src = kept_ranges(project)
exp0 = np.cumsum([0.0] + [b - a for a, b in src])


def split(a, b, ranges, starts):
    """The parts of [a, b] on the outer timeline, as (inner a, inner b) pieces."""
    out = []
    for (ra, rb), s0 in zip(ranges, starts):
        lo, hi = max(a, s0), min(b, s0 + rb - ra)
        if hi - lo > 1e-3:
            out.append((ra + lo - s0, ra + hi - s0))
    return out


def quietest(t, before, after, lo, hi):
    """Quietest 10 ms of the voice within [t - before, t + after], kept inside [lo, hi]."""
    i0, i1 = int(max(lo, t - before, 0) * 100), int(min(hi, t + after, len(venv) / 100 - 0.01) * 100)
    return (i0 + int(np.argmin(venv[i0:i1 + 1]))) / 100 if i1 > i0 else t


def keep_range(e):
    """The keep.json range that holds export time e, so a moved edge never reaches cut audio."""
    return next(((a, b) for a, b in keep if a - 1e-3 <= e <= b + 1e-3), (e, e))


def plan_pieces(short):
    """Pieces of the short in play order, each with its export range (the voice's timeline) and its
    source start (Take's files), plus each span's final-timeline edges after they move into silence."""
    hook = short["hook"] if isinstance(short["hook"][0], list) else [short["hook"]]
    spans = hook + short["body"]
    pieces, spans_out = [], []
    exact = lambda x: isinstance(x, str) and x.startswith("=")  # noqa: E731
    for k, (fa, fb, xa, xb) in enumerate((sec(a), sec(b), exact(a), exact(b)) for a, b in spans):
        exp = split(fa, fb, keep, fin0)
        if not exp:
            sys.exit(f"{short['slug']}: span {mmss(fa)}-{mmss(fb)} is outside the video")
        ea, lb = exp[0][0], exp[-1][1]
        # Whisper's word times run late, so search further back for the start and further on for the end.
        na = ea if xa else quietest(ea, 0.25, 0.05, keep_range(ea)[0], exp[0][1])
        nb = lb if xb else quietest(lb, 0.05, 0.25, exp[-1][0], keep_range(lb)[1])
        exp[0] = (na, exp[0][1])
        exp[-1] = (exp[-1][0], nb)
        spans_out.append({"fa": fa + na - ea, "fb": fb + nb - lb, "hook": k < len(hook)})
        for a, b in exp:
            for e0, (ra, rb) in zip(exp0, src):
                lo, hi = max(a, e0), min(b, e0 + rb - ra)
                if hi - lo > 0.05:  # shorter than 2 frames: not worth a piece
                    pieces.append({"ea": lo, "eb": hi, "sa": ra + lo - e0})
    return pieces, spans_out


def grab(path, t, scale, gray=True):
    """One frame at source time t, scaled, as a numpy array."""
    w, h = scale
    raw = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{t:.3f}", "-i", str(path), "-frames:v", "1", "-vf",
                          f"scale={w}:{h},format={'gray' if gray else 'rgb24'}", "-f", "rawvideo", "-"],
                         capture_output=True, check=True).stdout
    return np.frombuffer(raw, np.uint8).reshape(h, w) if gray else np.frombuffer(raw, np.uint8).reshape(h, w, 3)


def times_in(pieces, step):
    ts = [p["sa"] + x for p in pieces for x in np.arange(0.2, p["eb"] - p["ea"], step)]
    return ts[:: max(1, len(ts) // 60)]


def slide_box(pieces):
    """Bounding box of everything drawn on the slide during the short, in screen pixels. The deck's
    stage is 16:9 inside Take's wider frame, and nothing is drawn right of x 1560 on its canvas."""
    sw, sh = project["screen"]["width"], project["screen"]["height"]
    q = 4
    ink = np.zeros((sh // q, sw // q), bool)
    for t in times_in(pieces, 1.5):
        ink |= np.abs(grab(screen_file, t, (sw // q, sh // q)).astype(int) - BG[0]) > 14
    stage_w = min(sw, sh * 16 / 9)
    x0 = (sw - stage_w) / 2
    right = int((x0 + CONTENT_RIGHT / CANVAS_W * stage_w) / q)
    ink[:, right:] = False
    cols, rows = np.where(ink.sum(0) >= 2)[0], np.where(ink.sum(1) >= 2)[0]
    if not len(cols):
        return 0, 0, sw, sh
    pad = 28
    x, y = max(0, cols[0] * q - pad), max(0, rows[0] * q - pad)
    x2, y2 = min(sw, (cols[-1] + 1) * q + pad), min(sh, (rows[-1] + 1) * q + pad)
    return x, y, x2 - x, y2 - y


def face_box(pieces, override):
    """Camera crop for the bottom third: around the median detected face, head in the upper part."""
    cw0, ch0 = project["camera"]["width"], project["camera"]["height"]
    if override:
        cx, cy, cw = override
    else:
        import cv2
        det = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
        found = []
        for t in times_in(pieces, 6)[:10]:
            img = grab(camera_file, t, (cw0 // 2, ch0 // 2))
            f = det.detectMultiScale(img, 1.1, 6, minSize=(60, 60))
            if len(f):
                x, y, w, h = max(f, key=lambda r: r[2] * r[3])
                found.append((2 * (x + w / 2), 2 * (y + h / 2), 2 * h))
        if found:
            cx, cy, fh = np.median(np.array(found), 0)
            cw = min(cw0, max(900, 4.0 * fh))
            cy += 0.12 * cw * CAM_H / W
        else:
            print("  no face found, using the frame centre (set \"face\" in shorts.json to place it)")
            cx, cy, cw = cw0 / 2, ch0 / 2, cw0
    ch = cw * CAM_H / W
    if ch > ch0:
        ch, cw = ch0, ch0 * W / CAM_H
    x = min(max(0, cx - cw / 2), cw0 - cw)
    y = min(max(0, cy - ch / 2), ch0 - ch)
    ev = lambda v: int(v) // 2 * 2  # noqa: E731
    return ev(x), ev(y), ev(cw), ev(ch)


def font(path, size):
    return ImageFont.truetype(str(path), size)


def draw_card(d, text):
    """The hook card: up to 3 centred lines in the top band, *starred* words in orange."""
    for size in (74, 66, 58, 50):
        f = font(FONTS / "Montserrat-ExtraBold.ttf", size)
        toks, rows, row = text.split(), [], []
        for tok in toks:
            test = " ".join(x.strip("*") for x in row + [tok])
            if row and d.textlength(test, font=f) > 980:
                rows.append(row)
                row = []
            row.append(tok)
        rows.append(row)
        if len(rows) <= 3:
            break
    lh = size * 1.18
    y = (CARD_H - lh * len(rows)) / 2 + 20
    for row in rows:
        plain = [t.strip("*") for t in row]
        x = (W - d.textlength(" ".join(plain), font=f)) / 2
        on = False
        for tok in row:
            if tok.startswith("*"):
                on = True
            word = tok.strip("*")
            d.text((x, y), word, font=f, fill=ACCENT if on else INK)
            x += d.textlength(word + " ", font=f)
            if tok.endswith("*"):
                on = False
        y += lh


def phrases(ws):
    """Caption phrases: up to 4 words or 22 characters, broken at punctuation and pauses."""
    out, cur = [], []
    for i, w in enumerate(ws):
        cur.append(w)
        nxt = ws[i + 1] if i + 1 < len(ws) else None
        text = " ".join(x["word"] for x in cur)
        if (nxt is None or len(cur) >= 4 or len(text + nxt["word"]) > 22 or w["word"][-1:] in ".,?!:;"
                or nxt["start"] - w["end"] > 0.35):
            out.append(cur)
            cur = []
    return out


def draw_caption(d, phrase, active, cy):
    f = font(FONTS / "TikTokSans-Bold.ttf", 76)
    text = " ".join(w["word"] for w in phrase)
    rows = [phrase] if d.textlength(text, font=f) <= 1000 else [phrase[:len(phrase) // 2], phrase[len(phrase) // 2:]]
    lh = 92
    y = cy - lh * len(rows) / 2
    for row in rows:
        x = (W - d.textlength(" ".join(w["word"] for w in row), font=f)) / 2
        for w in row:
            d.text((x, y), w["word"], font=f, fill=ACCENT if w is active else INK)
            x += d.textlength(w["word"] + " ", font=f)
        y += lh


def render(n, short, defaults):
    slug = short["slug"]
    out_dir = work.parent / "shorts"
    out_dir.mkdir(exist_ok=True)
    tmp = work / "shorts-tmp" / slug
    shutil.rmtree(tmp, ignore_errors=True)
    tmp.mkdir(parents=True)
    pieces, spans = plan_pieces(short)

    # Picture and sound line up like render.py: each piece starts on a camera frame, its sound moves
    # with it, and the frame count follows the running sample count so nothing drifts.
    audio, frames, samples = [], 0, 0
    for p in pieces:
        d = round(p["sa"] * FPS) / FPS - p["sa"]
        p["sa"] += d
        p["ea"] += d
        p["eb"] += d
        s0, s1 = round(p["ea"] * SR), round(p["eb"] * SR)
        seg = voice[s0:s1].copy()
        k = min(len(seg) // 2, SR // 200)
        seg[:k] *= np.linspace(0, 1, k)
        seg[len(seg) - k:] *= np.linspace(1, 0, k)
        audio.append(seg)
        samples += s1 - s0
        p["nf"] = round(samples / SR * FPS) - frames
        frames += p["nf"]
    audio = np.concatenate(audio)
    total = frames / FPS
    hook_len = sum(s["fb"] - s["fa"] for s in spans if s["hook"])
    if not MIN_LEN <= total <= MAX_LEN:
        print(f"  warning: {slug} runs {total:.1f} s, outside {MIN_LEN} to {MAX_LEN} s")
    if hook_len > HOOK_MAX:
        print(f"  warning: {slug} hook runs {hook_len:.1f} s, over {HOOK_MAX} s")

    # loudness: the voice is already mastered, so a plain gain to -14 LUFS with a -1.5 dBFS ceiling
    wav = tmp / "audio.wav"
    sf.write(wav, audio, SR, subtype="FLOAT")
    log = subprocess.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(wav), "-af", "ebur128", "-f", "null", "-"],
                         capture_output=True, text=True).stderr
    lufs = float(log[log.rfind("Summary"):].split("I:")[1].split()[0])
    gain = min(10 ** ((-14 - lufs) / 20), 10 ** (-1.5 / 20) / max(1e-6, np.abs(audio).max()))
    sf.write(wav, audio * gain, SR, subtype="FLOAT")

    # layout
    bx, by, bw, bh = slide_box(pieces)
    scale = min((W - 60) / bw, (TOP - CARD_H - CAP_H) / bh)
    sw, sh = int(bw * scale) // 2 * 2, int(bh * scale) // 2 * 2
    sx, sy = (W - sw) // 2, CARD_H + (TOP - CARD_H - CAP_H - sh) // 2
    cap_y = (sy + sh + TOP) / 2
    fx, fy, fw, fh = face_box(pieces, short.get("face") or defaults.get("face"))

    # captions and card, one transparent frame per state, played with the concat demuxer
    ws, off = [], 0.0
    for k, s in enumerate(spans):
        for w in words:
            if s["fa"] <= (w["start"] + w["end"]) / 2 < s["fb"]:
                ws.append({**w, "start": max(0.0, w["start"] - s["fa"] + off), "end": w["end"] - s["fa"] + off, "span": k})
        off += s["fb"] - s["fa"]
    if ws:  # a hook often starts mid-sentence
        ws[0]["word"] = ws[0]["word"][:1].upper() + ws[0]["word"][1:]
    events = []
    for ph in phrases(ws):
        for i, w in enumerate(ph):
            t1 = ph[i + 1]["start"] if i + 1 < len(ph) else w["end"] + 0.25
            events.append((w["start"], t1, ph, w))
    states, t = [], 0.0
    for a, b, ph, w in events:
        if a > t + 1e-3:
            states.append((t, a, None, None))
        a = max(a, t)
        if b > a:
            states.append((a, b, ph, w))
            t = b
    states.append((t, total + 1, None, None))
    lst = []
    for i, (a, b, ph, w) in enumerate(states):
        img = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        d = ImageDraw.Draw(img)
        draw_card(d, short["card"])
        if ph:
            draw_caption(d, ph, w, cap_y)
        img.save(tmp / f"{i:04d}.png", compress_level=1)
        lst.append(f"file '{tmp / f'{i:04d}.png'}'\nduration {b - a:.4f}")
    lst.append(f"file '{tmp / f'{len(states) - 1:04d}.png'}'")
    (tmp / "overlay.txt").write_text("\n".join(lst) + "\n")

    args, g = [], []
    for i, p in enumerate(pieces):
        d = p["nf"] / FPS + 0.5
        for f in (screen_file, camera_file):
            args += ["-ss", f"{p['sa']:.6f}", "-t", f"{d:.3f}", "-i", str(f)]
        g.append(f"[{2 * i}:v]fps={FPS}:start_time=0,trim=end_frame={p['nf']},setpts=PTS-STARTPTS,"
                 f"crop={bw}:{bh}:{bx}:{by},scale={sw}:{sh}:flags=lanczos:{RGB_IN},format=rgb24,setsar=1[s{i}];")
        g.append(f"[{2 * i + 1}:v]fps={FPS}:start_time=0,trim=end_frame={p['nf']},setpts=PTS-STARTPTS,"
                 f"crop={fw}:{fh}:{fx}:{fy},scale={W}:{CAM_H}:flags=lanczos:{RGB_IN},format=rgb24{',hflip' if mirror else ''},setsar=1[c{i}];")
    k, ov = len(pieces), 2 * len(pieces)
    g.append("".join(f"[s{i}]" for i in range(k)) + f"concat=n={k}:v=1:a=0[slide];")
    g.append("".join(f"[c{i}]" for i in range(k)) + f"concat=n={k}:v=1:a=0[cam];")
    g.append(f"color=c=0x{BG[0]:02x}{BG[1]:02x}{BG[2]:02x}:s={W}x{H}:r={FPS}:d={total:.4f},format=rgb24[bg];")
    g.append(f"[{ov}:v]fps={FPS}:start_time=0,format=rgba,trim=end_frame={frames}[txt];")
    g.append(f"[bg][slide]overlay={sx}:{sy}:format=rgb[t1];[t1][cam]overlay=0:{TOP}:format=rgb[t2];"
             f"[t2][txt]overlay=0:0:format=rgb,scale=out_color_matrix=bt709:out_range=tv,format=yuv420p[v]")
    (tmp / "graph.txt").write_text("\n".join(g))
    out = out_dir / f"{n} {slug}.mp4"
    run("ffmpeg", "-v", "error", "-y", *args, "-f", "concat", "-safe", "0", "-i", tmp / "overlay.txt", "-i", wav,
        "-filter_complex_script", tmp / "graph.txt", "-map", "[v]", "-map", f"{ov + 1}:a", "-frames:v", frames,
        "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-r", FPS, "-color_primaries", "bt709",
        "-color_trc", "bt709", "-colorspace", "bt709", "-c:a", "aac", "-b:a", "256k", "-ar", SR, "-ac", "2",
        "-movflags", "+faststart", out)

    # check lip sync: the short's sound against the camera's own mic over the same source pieces
    got = np.frombuffer(subprocess.run(["ffmpeg", "-v", "error", "-i", str(out), "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"],
                                       capture_output=True, check=True).stdout, np.float32)
    mic = np.concatenate([np.frombuffer(subprocess.run(
        ["ffmpeg", "-v", "error", "-ss", f"{p['sa']:.6f}", "-i", str(camera_file), "-t", f"{p['nf'] / FPS:.4f}", "-vn", "-ac", "1",
         "-ar", str(SR), "-f", "f32le", "-"], capture_output=True, check=True).stdout, np.float32) for p in pieces])

    def env(x):
        q = SR // 1000
        return np.sqrt((x[:len(x) // q * q].reshape(-1, q) ** 2).mean(1))
    eg, em = env(got), env(mic)
    offsets = []
    for t0 in range(2, int(min(len(eg), len(em)) / 1000) - 8, 15):
        a = em[t0 * 1000:(t0 + 6) * 1000]
        b = eg[t0 * 1000 - 200:(t0 + 6) * 1000 + 200]
        a = (a - a.mean()) / (a.std() + 1e-9)
        offsets.append(int(np.argmax(np.correlate(b - b.mean(), a, "valid")) - 200))

    # contact sheet: cover frame, end of the hook, just after the cut, middle, end
    marks = [0.0, max(0.0, hook_len - 0.3), min(total - 0.5, hook_len + 1.0), total / 2, total - 1.0]
    sheet = Image.new("RGB", (len(marks) * 360, 640), "white")
    for i, t in enumerate(marks):
        fr = grab(out, t, (360, 640), gray=False)
        sheet.paste(Image.fromarray(fr), (i * 360, 0))
    sheet.save(out.with_suffix(".jpg"), quality=88)
    hook_text = " ".join(w["word"] for w in ws if spans[w["span"]]["hook"])
    print(f"{out.name}: {mmss(total)}, hook {hook_len:.1f} s, {k} pieces, slide x{scale:.2f}, "
          f"{lufs + 20 * np.log10(gain):.1f} LUFS, sync vs camera mic (ms): {offsets}")
    shutil.rmtree(tmp, ignore_errors=True)
    return {"n": n, "file": out.name, "length": mmss(total), "hook_text": hook_text, **short}


defaults = {k: v for k, v in spec.items() if k != "shorts"}
done = []
for n, short in enumerate(spec["shorts"], 1):
    if only in (None, n):
        done.append(render(n, short, defaults))
if only is None:
    md = ["# Shorts", ""]
    for r in done:
        md += [f"## {r['n']}. {r['title']}", "", f"- File: `{r['file']}` ({r['length']})",
               f"- Card: {r['card'].replace('*', '')}", f"- Hook (plays first): \"{r['hook_text']}\"",
               f"- Body: " + ", ".join(f"{a} to {b}" for a, b in r["body"]), f"- Why: {r.get('why', '')}", ""]
        if r.get("description"):
            md += [textwrap.fill(r["description"], 100), ""]
    (work.parent / "shorts" / "shorts.md").write_text("\n".join(md))
    shutil.rmtree(work / "shorts-tmp", ignore_errors=True)
