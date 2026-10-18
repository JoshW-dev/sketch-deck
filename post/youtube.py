"""Upload shorts to the Josh Wade AI channel and read a video's audience retention, with the YouTube
Data and Analytics APIs. Standard library only.

  python3 post/youtube.py auth --client-env ~/code/clipper/.env   # once: Google consent in the browser
  python3 post/youtube.py whoami                                   # which channel the token posts to
  python3 post/youtube.py short "<NN slug>" <n> --at "2026-10-15 12:00" [--confirm]
  python3 post/youtube.py list                                     # recent uploads, privacy, publishAt
  python3 post/youtube.py retention <video id> "<NN slug>"         # where viewers left, 7 to 10 days after upload

`short` is a dry run until --confirm. With --at (local time) it uploads private and YouTube makes it
public at that time; without --at it goes public at once. Each upload is recorded in
shorts/uploads.json, and a short that's already there is refused.

`retention` saves the audience-retention curve (upload day to today, in percents) as
work/retention.csv in the release folder. Then it runs lint/retention.py on it with the video's
length and the newest "(final...).srt", and saves the report as work/retention.txt. Analytics runs
about 3 days behind. The youtube.readonly scope covers it.

The OAuth client is Highstyle's (Google project 386527410978). Its uploads land public, which a
project created after 2020-07-28 can't do until it passes Google's audit, so don't swap in a new
project. It shares that project's 100 uploads a day with the Highstyle channels. The token and
client live in ~/.config/sketch-deck/youtube.json (mode 600), never in this public repo."""
import argparse
import csv
import datetime as dt
import http.server
import json
import os
import re
import secrets
import socket
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from zoneinfo import ZoneInfo

CONFIG = Path.home() / ".config/sketch-deck/youtube.json"
ROOT = Path(os.environ.get("SKETCH_POST_OUT", Path.home() / "Movies/Josh Wade AI"))
SCOPES = ["https://www.googleapis.com/auth/youtube.upload",
          "https://www.googleapis.com/auth/youtube.readonly",
          "https://www.googleapis.com/auth/youtube.force-ssl"]  # force-ssl lets us pull a bad upload back to private
API = "https://www.googleapis.com/youtube/v3"
ANALYTICS = "https://youtubeanalytics.googleapis.com/v2/reports"
LINT = Path(__file__).resolve().parent / "lint"
EDUCATION = "27"


def load_config():
    if not CONFIG.exists():
        sys.exit(f"no {CONFIG}: run `python3 post/youtube.py auth --client-env ~/code/clipper/.env` first")
    return json.loads(CONFIG.read_text())


def save_config(cfg):
    CONFIG.parent.mkdir(parents=True, exist_ok=True)
    old = os.umask(0o077)
    try:
        CONFIG.write_text(json.dumps(cfg, indent=1))
    finally:
        os.umask(old)
    CONFIG.chmod(0o600)


def post_form(url, fields):
    req = urllib.request.Request(url, urllib.parse.urlencode(fields).encode(), method="POST")
    return call(req)


def call(req):
    try:
        with urllib.request.urlopen(req) as r:
            body = r.read()
            return json.loads(body) if body else {}
    except urllib.error.HTTPError as e:
        sys.exit(f"{req.get_method()} {req.full_url.split('?')[0]} failed: {e.code} {e.read().decode()[:600]}")


def access_token(cfg):
    t = post_form("https://oauth2.googleapis.com/token", {
        "client_id": cfg["client_id"], "client_secret": cfg["client_secret"],
        "refresh_token": cfg["refresh_token"], "grant_type": "refresh_token"})
    return t["access_token"]


def api(token, method, path, params=None, body=None):
    url = f"{API}/{path}" + ("?" + urllib.parse.urlencode(params) if params else "")
    req = urllib.request.Request(url, json.dumps(body).encode() if body is not None else None, method=method)
    req.add_header("Authorization", f"Bearer {token}")
    if body is not None:
        req.add_header("Content-Type", "application/json")
    return call(req)


def my_channel(token):
    items = api(token, "GET", "channels", {"part": "snippet", "mine": "true"}).get("items", [])
    if not items:
        sys.exit("this Google account has no YouTube channel")
    return items[0]["id"], items[0]["snippet"]["title"]


def read_env(path):
    out = {}
    for line in Path(path).expanduser().read_text().splitlines():
        if "=" in line and not line.lstrip().startswith("#"):
            k, v = line.split("=", 1)
            out[k.strip()] = v.strip().strip('"').strip("'")
    return out


def cmd_auth(args):
    env = read_env(args.client_env)
    cid, secret, redirect = env["YOUTUBE_CLIENT_ID"], env["YOUTUBE_CLIENT_SECRET"], env["YOUTUBE_REDIRECT_URI"]
    u = urllib.parse.urlparse(redirect)
    state = secrets.token_urlsafe(16)
    got = {}

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            q = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            if urllib.parse.urlparse(self.path).path != u.path:
                self.send_response(404)
                self.end_headers()
                return
            got.update({k: v[0] for k, v in q.items()})
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.end_headers()
            self.wfile.write(b"Done. You can close this tab and go back to Claude.")

        def log_message(self, *a):
            pass

    url = "https://accounts.google.com/o/oauth2/v2/auth?" + urllib.parse.urlencode({
        "client_id": cid, "redirect_uri": redirect, "response_type": "code", "scope": " ".join(SCOPES),
        "access_type": "offline", "prompt": "consent select_account", "state": state})
    # A browser may send "localhost" to ::1 or to 127.0.0.1, so listen on both. On 2026-10-14 an
    # IPv4-only listener never got Google's redirect.
    class Server6(http.server.HTTPServer):
        address_family = socket.AF_INET6
    servers = [http.server.HTTPServer(("127.0.0.1", u.port), Handler)]
    try:
        servers.append(Server6(("::1", u.port), Handler))
    except OSError as e:
        print(f"no IPv6 listener ({e}), IPv4 only")
    for srv in servers:
        threading.Thread(target=srv.serve_forever, daemon=True).start()
    print("opening Google consent in your browser. Sign in as the account that owns the Josh Wade AI channel.")
    print(f"if no tab opens, paste this into the browser:\n{url}", flush=True)
    subprocess.run(["open", url])
    deadline = dt.datetime.now() + dt.timedelta(minutes=15)
    while "code" not in got and "error" not in got and dt.datetime.now() < deadline:
        time.sleep(0.5)
    for srv in servers:
        srv.shutdown()
    if not got:
        sys.exit("no answer from Google within 15 minutes")
    if got.get("error") or got.get("state") != state:
        sys.exit(f"consent failed: {got.get('error', 'state mismatch')}")
    t = post_form("https://oauth2.googleapis.com/token", {
        "client_id": cid, "client_secret": secret, "code": got["code"], "redirect_uri": redirect,
        "grant_type": "authorization_code"})
    if "refresh_token" not in t:
        sys.exit("Google returned no refresh token")
    channel_id, title = my_channel(t["access_token"])
    save_config({"client_id": cid, "client_secret": secret, "refresh_token": t["refresh_token"],
                 "scope": t.get("scope", ""), "channel_id": channel_id, "channel_title": title,
                 "connected": dt.datetime.now().astimezone().isoformat(timespec="seconds")})
    print(f"connected: {title} ({channel_id}), saved to {CONFIG}")


def checked_token(cfg):
    """A fresh access token, after checking it still posts to the channel connected at auth time."""
    token = access_token(cfg)
    channel_id, title = my_channel(token)
    if channel_id != cfg["channel_id"]:
        sys.exit(f"token now posts to {title} ({channel_id}), expected {cfg['channel_title']} ({cfg['channel_id']})")
    return token, title


def cmd_whoami(args):
    cfg = load_config()
    _, title = checked_token(cfg)
    print(f"{title} ({cfg['channel_id']}), connected {cfg['connected']}")


def cmd_list(args):
    cfg = load_config()
    token, _ = checked_token(cfg)
    ch = api(token, "GET", "channels", {"part": "contentDetails", "id": cfg["channel_id"]})["items"][0]
    uploads = ch["contentDetails"]["relatedPlaylists"]["uploads"]
    ids = [i["contentDetails"]["videoId"] for i in api(token, "GET", "playlistItems", {
        "part": "contentDetails", "playlistId": uploads, "maxResults": 15}).get("items", [])]
    if not ids:
        return print("no uploads")
    for v in api(token, "GET", "videos", {"part": "snippet,status", "id": ",".join(ids)})["items"]:
        s = v["status"]
        when = f" publishAt {s['publishAt']}" if s.get("publishAt") else ""
        print(f"{v['id']}  {s['privacyStatus']:<8}{when}  {v['snippet']['title']}")


def cmd_short(args):
    folder = ROOT / args.release
    spec = json.loads((folder / "work/shorts.json").read_text())
    short = spec["shorts"][args.n - 1]
    files = list((folder / "shorts").glob(f"{args.n} *.mp4"))
    if len(files) != 1:
        sys.exit(f"expected one shorts/{args.n} *.mp4 in {folder}, found {len(files)}")
    video = files[0]
    log_file = folder / "shorts/uploads.json"
    log = json.loads(log_file.read_text()) if log_file.exists() else []
    if any(r["n"] == args.n for r in log) and not args.force:
        sys.exit(f"short {args.n} is already uploaded: {[r['url'] for r in log if r['n'] == args.n][0]}")

    title = short["title"][:100]
    desc = short.get("description") or short["card"].replace("*", "")
    if spec.get("full_video") and spec["full_video"] not in desc:
        body, _, tags = desc.rpartition("\n\n") if desc.rsplit("\n\n", 1)[-1].startswith("#") else (desc, "", "")
        desc = f"{body}\n\nFull video: {spec['full_video']}" + (f"\n\n{tags}" if tags else "")
    status = {"selfDeclaredMadeForKids": False, "containsSyntheticMedia": False, "embeddable": True}
    if args.at:
        at = dt.datetime.fromisoformat(args.at).astimezone()
        if at <= dt.datetime.now().astimezone() + dt.timedelta(minutes=15):
            sys.exit(f"--at {args.at} is less than 15 minutes from now")
        status.update(privacyStatus="private", publishAt=at.astimezone(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"))
    else:
        status["privacyStatus"] = "public"
    meta = {"snippet": {"title": title, "description": desc, "tags": spec.get("tags", []), "categoryId": EDUCATION,
                        "defaultLanguage": "en", "defaultAudioLanguage": "en"}, "status": status}
    when = f"public at {at:%a %Y-%m-%d %H:%M %Z}" if args.at else "public NOW"
    print(f"{video.name} ({video.stat().st_size / 1e6:.1f} MB), {when}\ntitle: {title}\ndescription:\n{desc}\n")
    if not args.confirm:
        return print("dry run. Add --confirm to upload.")

    cfg = load_config()
    token, channel = checked_token(cfg)
    url = "https://www.googleapis.com/upload/youtube/v3/videos?" + urllib.parse.urlencode(
        {"uploadType": "resumable", "part": "snippet,status"})
    req = urllib.request.Request(url, json.dumps(meta).encode(), method="POST")
    for k, v in {"Authorization": f"Bearer {token}", "Content-Type": "application/json; charset=UTF-8",
                 "X-Upload-Content-Type": "video/mp4", "X-Upload-Content-Length": str(video.stat().st_size)}.items():
        req.add_header(k, v)
    try:
        with urllib.request.urlopen(req) as r:
            session = r.headers["Location"]
    except urllib.error.HTTPError as e:
        sys.exit(f"upload refused: {e.code} {e.read().decode()[:600]}")
    put = urllib.request.Request(session, video.read_bytes(), method="PUT")
    put.add_header("Content-Type", "video/mp4")
    v = call(put)
    rec = {"n": args.n, "slug": short["slug"], "id": v["id"], "url": f"https://youtube.com/shorts/{v['id']}",
           "privacy": v["status"]["privacyStatus"], "publishAt": v["status"].get("publishAt"),
           "uploaded": dt.datetime.now().astimezone().isoformat(timespec="seconds"), "channel": channel}
    log.append(rec)
    log_file.write_text(json.dumps(log, indent=1))
    print(f"uploaded to {channel}: {rec['url']} ({rec['privacy']}{', publishes ' + rec['publishAt'] if rec['publishAt'] else ''})")


def iso_seconds(d):
    """Seconds in an ISO 8601 duration such as PT7M23S."""
    m = re.fullmatch(r"P(?:(\d+)D)?(?:T(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?)?", d)
    if not m:
        sys.exit(f"can't read the video length {d!r}")
    days, h, mins, s = (int(x or 0) for x in m.groups())
    return days * 86400 + h * 3600 + mins * 60 + s


def cmd_retention(args):
    folder = ROOT / args.release
    if not folder.is_dir():
        sys.exit(f"no release folder {folder}")
    if args.transcript:
        srt = Path(args.transcript).expanduser()
    else:
        srt = max(folder.glob("*(final*).srt"), key=lambda f: f.stat().st_mtime, default=None)
    cfg = load_config()
    token, channel = checked_token(cfg)
    items = api(token, "GET", "videos", {"part": "snippet,contentDetails", "id": args.video_id}).get("items", [])
    if not items:
        sys.exit(f"YouTube has no video {args.video_id}")
    v = items[0]
    if v["snippet"]["channelId"] != cfg["channel_id"]:
        sys.exit(f"{args.video_id} belongs to {v['snippet']['channelTitle']}, not {channel}")
    seconds = args.duration or iso_seconds(v["contentDetails"]["duration"])
    # Analytics days are Pacific time, so start on the upload's Pacific date
    pacific = ZoneInfo("America/Los_Angeles")
    published = dt.datetime.fromisoformat(v["snippet"]["publishedAt"].replace("Z", "+00:00"))
    start, end = published.astimezone(pacific).date(), dt.datetime.now(pacific).date()
    req = urllib.request.Request(ANALYTICS + "?" + urllib.parse.urlencode({
        "ids": "channel==MINE", "startDate": start.isoformat(), "endDate": end.isoformat(),
        "dimensions": "elapsedVideoTimeRatio", "metrics": "audienceWatchRatio,relativeRetentionPerformance",
        "filters": f"video=={args.video_id}"}))
    req.add_header("Authorization", f"Bearer {token}")
    report = call(req)
    if not report.get("rows"):
        sys.exit(f"no retention data for {args.video_id} from {start} to {end} yet. Analytics runs about 3 days behind.")
    col = {c["name"]: i for i, c in enumerate(report["columnHeaders"])}
    rows = sorted(report["rows"], key=lambda r: r[col["elapsedVideoTimeRatio"]])
    # lint/retention.py reads percents. Left as ratios, a curve that loses 71% reads as "0.8% lost, healthy".
    csv_file = folder / "work/retention.csv"
    csv_file.parent.mkdir(exist_ok=True)
    with csv_file.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["elapsed_pct", "watching_pct", "relative_retention_performance"])
        for r in rows:
            w.writerow([round(r[col["elapsedVideoTimeRatio"]] * 100, 2), round(r[col["audienceWatchRatio"]] * 100, 2),
                        r[col["relativeRetentionPerformance"]]])
    print(f"{v['snippet']['title']} ({args.video_id}): {len(rows)} points, {start} to {end}, {seconds:g} s long")
    print(f"saved {csv_file}")
    print(f"transcript: {srt.name}" if srt else "no (final).srt here, so the report can't say what was said at each drop")
    cmd = [sys.executable, str(LINT / "retention.py"), str(csv_file), "--duration", f"{seconds:g}"]
    if srt:
        cmd += ["--transcript", str(srt)]
    out = subprocess.run(cmd, capture_output=True, text=True)
    if out.returncode:
        sys.exit(f"lint/retention.py failed:\n{out.stdout}{out.stderr}")
    (folder / "work/retention.txt").write_text(out.stdout)
    print(out.stdout)


p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
sub = p.add_subparsers(dest="cmd", required=True)
a = sub.add_parser("auth")
a.add_argument("--client-env", required=True, help="a .env with YOUTUBE_CLIENT_ID, _SECRET and _REDIRECT_URI")
sub.add_parser("whoami")
sub.add_parser("list")
s = sub.add_parser("short")
s.add_argument("release", help='release folder name, e.g. "01 AI bottlenecks"')
s.add_argument("n", type=int)
s.add_argument("--at", help='local time to go public, e.g. "2026-10-15 12:00"')
s.add_argument("--confirm", action="store_true")
s.add_argument("--force", action="store_true", help="upload again even if uploads.json has it")
r = sub.add_parser("retention")
r.add_argument("video_id", help="the long video's id, from `list`")
r.add_argument("release", help='release folder name, e.g. "01 AI bottlenecks"')
r.add_argument("--duration", type=float, help="length in seconds (default: YouTube's)")
r.add_argument("--transcript", help='an .srt in final-video time (default: the newest "(final...).srt")')
args = p.parse_args()
{"auth": cmd_auth, "whoami": cmd_whoami, "list": cmd_list, "short": cmd_short,
 "retention": cmd_retention}[args.cmd](args)
