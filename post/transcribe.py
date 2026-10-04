"""Step 3. Two transcripts of the mastered voice. words.json is the clean one for captions.
words-disfluent.json uses a prompt that makes Whisper keep "um" and "uh", for finding cuts.

Usage: uv run --quiet --python 3.11 --with mlx-whisper python post/transcribe.py <workdir> ["names, terms"]"""
import json
import sys
from pathlib import Path

import mlx_whisper

sys.path.insert(0, str(Path(__file__).parent))
from common import WHISPER  # noqa: E402

work = Path(sys.argv[1]).expanduser()
terms = sys.argv[2] if len(sys.argv) > 2 else ""
audio = str(work / "voice.wav")
clean = mlx_whisper.transcribe(audio, path_or_hf_repo=WHISPER, word_timestamps=True, language="en",
                               initial_prompt=f"Josh Wade. {terms}".strip())
json.dump(clean, open(work / "words.json", "w"), indent=1)
# Whisper only applies a prompt to its first 30 s window, and after that it stops writing fillers.
# So the disfluent pass runs on 20 to 28 s chunks cut in pauses, each with the prompt.
import numpy as np
import soundfile as sf
y, sr = sf.read(audio, dtype="float32")
hop = sr // 100
env = 20 * np.log10(np.sqrt((y[:len(y) // hop * hop].reshape(-1, hop) ** 2).mean(1)) + 1e-9)
quiet = env < np.percentile(env, 90) - 30
cuts, t = [0], 0
while len(y) / sr - t > 28:
    lo, hi = int((t + 20) * 100), int((t + 28) * 100)
    run_len, best, bi = 0, -1, hi
    for i in range(lo, hi):
        run_len = run_len + 1 if quiet[i] else 0
        if run_len > best:
            best, bi = run_len, i - run_len // 2
    t = bi / 100
    cuts.append(t)
cuts.append(len(y) / sr)
segments = []
for a, b in zip(cuts, cuts[1:]):
    sf.write(work / "piece.wav", y[int(a * sr):int(b * sr)], sr)
    r = mlx_whisper.transcribe(str(work / "piece.wav"), path_or_hf_repo=WHISPER, word_timestamps=True, language="en",
                               initial_prompt="Umm, so, uh, I was like, I- I think, um, you know, that's, uh, hmm. Okay so, like, um.")
    for s in r["segments"]:
        s["words"] = [{**x, "start": x["start"] + a, "end": x["end"] + a} for x in s.get("words", [])]
        if s["words"]:
            segments.append({"text": s["text"], "words": s["words"]})
json.dump({"segments": segments}, open(work / "words-disfluent.json", "w"), indent=1)
print(f"disfluent pass: {len(cuts) - 1} chunks, "
      f"{sum(x['word'].strip(' ,.').lower() in ('um', 'uh', 'umm') for s in segments for x in s['words'])} fillers")
print(f"{len(clean['segments'])} segments")
