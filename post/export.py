"""Step 1. Export the Take recording at 1440p, with the camera bubble moved in far enough that a
centred 16:9 crop keeps it. Take's own bundle is never touched: the export runs from a copy whose
media files are symlinks.

Usage: python3 post/export.py "<recording>.take" <workdir>
Writes <workdir>/video.mp4 (Take's export, wider than 16:9) and <workdir>/frame.json (the crop)."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from common import run, save  # noqa: E402

TAKE = Path.home() / "code/take/build/Take.app/Contents/MacOS/Take"
HEIGHT = 1440

bundle, work = Path(sys.argv[1]).expanduser(), Path(sys.argv[2]).expanduser()
work.mkdir(parents=True, exist_ok=True)
copy = work / "export.take"
copy.mkdir(exist_ok=True)
for f in bundle.iterdir():
    if f.name != "project.json" and not (copy / f.name).exists():
        (copy / f.name).symlink_to(f)

project = json.load(open(bundle / "project.json"))
sw, sh = project["screen"]["width"], project["screen"]["height"]
width = round(HEIGHT * sw / sh) & ~1
# The deck stage is 16:9; whatever is left over is blank margin on two sides.
if width * 9 > HEIGHT * 16:
    crop = {"w": HEIGHT * 16 // 9, "h": HEIGHT, "x": (width - HEIGHT * 16 // 9) // 2, "y": 0}
    trim = crop["x"]
else:
    h = width * 9 // 16 & ~1
    crop = {"w": width, "h": h, "x": 0, "y": (HEIGHT - h) // 2}
    trim = crop["y"]
# Take places the bubble margin * height in from both edges, so push it in by the trimmed amount.
project["bubble"]["margin"] = project["bubble"].get("margin", 0.03) + trim / HEIGHT
project["export"] = {**project.get("export", {}), "height": HEIGHT, "frame": "matchScreen"}
json.dump(project, open(copy / "project.json", "w"), indent=2)

out = work / "video.mp4"
run(TAKE, "--export", copy, out)
save(work / "frame.json", {"export": [width, HEIGHT], "crop": crop})
print(f"crop {crop['w']}x{crop['h']} at {crop['x']},{crop['y']}")
