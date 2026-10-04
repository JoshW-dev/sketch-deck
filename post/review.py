"""Step 6. Write review.html next to the final video: the raw mic against the finished voice on the
same 30 s, the final video with a button for every cut, and the thumbnails.

Usage: ~/.cache/sketch-deck-post/venv-audio/bin/python post/review.py <workdir> "<Title>"
Then: open "<workdir>/../review.html" """
import html
import sys
from pathlib import Path
from urllib.parse import quote

sys.path.insert(0, str(Path(__file__).parent))
from common import load, run  # noqa: E402

work, title = Path(sys.argv[1]).expanduser(), sys.argv[2]
top = work.parent
listen = work / "listen"
listen.mkdir(exist_ok=True)
for name, src in [("before", "raw-norm.wav"), ("after", "voice.wav")]:
    run("ffmpeg", "-v", "error", "-y", "-ss", 60, "-t", 30, "-i", work / src, "-af", "loudnorm=I=-16:TP=-1.5:LRA=11",
        "-ac", 2, "-ar", 48000, "-c:a", "pcm_s16le", listen / f"{name}.wav")
rel = lambda p: quote(str(p.relative_to(top)))  # noqa: E731
cuts = load(work / "cuts-final.json")
buttons = "\n".join(
    f'  <button data-t="{c["at"]}"><b>{int(c["at"] // 60)}:{int(c["at"] % 60):02d}</b> {html.escape(c["label"])}'
    f' <span>{c["length"]:.1f} s</span></button>' for c in cuts)
thumbs = "\n".join(f'<img src="{rel(p)}" alt="{html.escape(p.stem)}">' for p in sorted(top.glob("thumbnail*.png")))
page = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)} review</title>
<style>
  html, body {{ background: #ffffff; color: #1e1e1e; margin: 0; }}
  body {{ font: 16px/1.5 -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; max-width: 980px; margin: 0 auto; padding: 32px 16px 64px; }}
  h1 {{ font-size: 26px; margin: 0 0 4px; }}
  h2 {{ font-size: 18px; margin: 36px 0 12px; padding-top: 20px; border-top: 1px solid #e9ecef; }}
  p {{ margin: 0 0 12px; color: #495057; }}
  video, img {{ width: 100%; border: 1px solid #e9ecef; border-radius: 8px; }}
  img {{ margin-bottom: 12px; }}
  .pair, .cuts {{ display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }}
  .clip {{ border: 1px solid #e9ecef; border-radius: 8px; padding: 12px 14px; }}
  .clip.pick {{ background: #ebfbee; border-color: #b2f2bb; }}
  audio {{ width: 100%; margin-top: 6px; }}
  .cuts {{ gap: 8px; margin-top: 12px; }}
  .cuts button {{ text-align: left; font: inherit; font-size: 14px; padding: 8px 10px; border: 1px solid #e9ecef; border-radius: 8px; background: #fff; cursor: pointer; }}
  .cuts button:hover {{ background: #f8f9fa; }}
  .cuts button span {{ color: #868e96; float: right; }}
  @media (max-width: 640px) {{ .pair, .cuts {{ grid-template-columns: 1fr; }} }}
</style></head><body>
<h1>{html.escape(title)}: review before upload</h1>
<p>Both clips are 1:00 to 1:30 of the recording at the same loudness.</p>
<h2>1. Voice</h2>
<div class="pair">
  <div class="clip"><b>Before: raw laptop mic</b><audio controls preload="auto" src="{rel(listen / 'before.wav')}"></audio></div>
  <div class="clip pick"><b>After: in the final video</b><audio controls preload="auto" src="{rel(listen / 'after.wav')}"></audio></div>
</div>
<h2>2. Final video</h2>
<p>Click a cut to play from 2 seconds before it.</p>
<video id="v" controls preload="metadata" src="{quote(title + ' (final).mp4')}"></video>
<div class="cuts">
{buttons}
</div>
<h2>3. Thumbnails</h2>
{thumbs or '<p>None yet. Render them with npm run thumb in sketch-deck.</p>'}
<script>
  const v = document.getElementById('v');
  document.querySelectorAll('.cuts button').forEach(b => b.addEventListener('click', () => {{ v.currentTime = Math.max(0, +b.dataset.t - 2); v.play(); }}));
  document.querySelectorAll('audio, video').forEach(el => el.addEventListener('play', () => {{
    document.querySelectorAll('audio, video').forEach(o => {{ if (o !== el) o.pause(); }});
  }}));
</script>
</body></html>
"""
(top / "review.html").write_text(page)
print(f'open "{top / "review.html"}"')
