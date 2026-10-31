#!/usr/bin/env python3
"""Turn every `ytsearch1:...` entry in the playlist pack into a real, verified YouTube watch URL.

    python resolve_urls.py            # fix all *.json next to this script (backup *.json.bak first)
    python resolve_urls.py --dry-run  # show what would change, write nothing
    python resolve_urls.py thai_pop.json kpop.json

Needs yt-dlp (`pip install yt-dlp`, or yt-dlp.exe on PATH / --ytdlp PATH) and internet access.
For each entry the top search results are looked up; the first real, non-live video wins and the entry becomes
    source   = https://www.youtube.com/watch?v=<id>      (id came from YouTube, not guessed)
    title    = the video's real title
    duration = seconds
    query    = the original search text (kept so the entry can be re-resolved later)
Entries that are already URLs are left alone, so the script can be re-run (it resumes after a failure
or Ctrl+C). Entries with no usable result are left unchanged and listed at the end (exit code 1).
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

SEARCH = re.compile(r"^ytsearch\d*:(?P<q>.+)$", re.I | re.S)
URL = re.compile(r"^https://www\.youtube\.com/watch\?v=[A-Za-z0-9_-]{11}$")
VIDEO_ID = re.compile(r"^[A-Za-z0-9_-]{11}$")
CANDIDATES = 3  # search results examined per query


def search(query: str, exe: str | None) -> list[dict]:
    target = f"ytsearch{CANDIDATES}:{query}"
    if exe:
        r = subprocess.run(
            [exe, "--dump-single-json", "--flat-playlist", "--no-warnings", "--skip-download", target],
            capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=120, check=False,
        )
        if r.returncode != 0:
            raise RuntimeError((r.stderr.strip().splitlines() or [f"exit {r.returncode}"])[-1])
        info = json.loads(r.stdout)
    else:
        import yt_dlp

        opts = {"quiet": True, "no_warnings": True, "skip_download": True, "extract_flat": "in_playlist"}
        with yt_dlp.YoutubeDL(opts) as y:
            info = y.extract_info(target, download=False) or {}
    return [e for e in (info.get("entries") or []) if e]


def pick(results: list[dict]) -> dict | None:
    """First result that is a real video: valid 11-char id, known duration (live streams have none)."""
    for e in results:
        vid = str(e.get("id") or "")
        if VIDEO_ID.match(vid) and e.get("duration") and e.get("title"):
            return {"source": f"https://www.youtube.com/watch?v={vid}", "title": e["title"], "duration": float(e["duration"])}
    return None


def fix_entry(entry: dict, lookup) -> str:
    """Mutate one playlist entry. Returns 'ok' | 'skip' | 'fail:<why>'."""
    src = str(entry.get("source") or "").strip()
    if URL.match(src):
        return "skip"
    m = SEARCH.match(src)
    if not m:
        return f"fail:unrecognised source {src!r}"
    q = m["q"].strip()
    try:
        hit = pick(lookup(q))
    except Exception as ex:  # network, yt-dlp, JSON ...
        return f"fail:{ex}"
    if not hit:
        return "fail:no playable result"
    entry["query"] = q
    entry.update(hit)
    return "ok"


def process_file(path: Path, lookup, dry: bool, delay: float) -> tuple[int, int, list[str]]:
    data = json.loads(path.read_text("utf-8-sig"))
    tracks = data["tracks"] if isinstance(data, dict) else data
    ok = skip = 0
    fails: list[str] = []
    for e in tracks:
        res = fix_entry(e, lookup)
        if res == "ok":
            ok += 1
            print(f"  ok   {e['source']}  {e['title'][:60]}")
            if not dry:
                _save(path, data)  # write as we go: an interrupted run loses nothing
            time.sleep(delay)
        elif res == "skip":
            skip += 1
        else:
            fails.append(f"{path.name}: {e.get('source')}  ({res[5:]})")
            print(f"  FAIL {e.get('source')}  ({res[5:]})")
    seen: set[str] = set()  # two queries may land on the same video
    uniq = [t for t in tracks if not (URL.match(t.get("source", "")) and (t["source"] in seen or seen.add(t["source"])))]
    if len(uniq) != len(tracks) and not dry:
        tracks[:] = uniq
        _save(path, data)
    return ok, skip, fails


def _save(path: Path, data) -> None:
    bak = path.with_name(path.name + ".bak")
    if not bak.exists():
        shutil.copyfile(path, bak)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", "utf-8")
    tmp.replace(path)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("files", nargs="*", help="playlist files (default: every *.json next to this script)")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--ytdlp", help="path to yt-dlp(.exe); default: the Python module, else PATH")
    ap.add_argument("--delay", type=float, default=0.5, help="seconds between lookups (default 0.5)")
    a = ap.parse_args(argv)
    exe = a.ytdlp
    try:
        import yt_dlp  # noqa: F401
        if not exe:
            exe = None
    except ImportError:
        exe = exe or shutil.which("yt-dlp")
        if not exe:
            print("yt-dlp not found: run `pip install yt-dlp` or pass --ytdlp PATH", file=sys.stderr)
            return 2
    here = Path(__file__).resolve().parent
    files = [Path(f) for f in a.files] or sorted(here.glob("*.json"))
    total_ok = total_skip = 0
    all_fails: list[str] = []
    for f in files:
        print(f.name)
        o, s, fl = process_file(f, lambda q: search(q, exe), a.dry_run, a.delay)
        total_ok, total_skip = total_ok + o, total_skip + s
        all_fails += fl
    print(f"\nresolved {total_ok}, already URLs {total_skip}, failed {len(all_fails)}" + (" (dry run: nothing written)" if a.dry_run else ""))
    for line in all_fails:
        print("  could not resolve:", line)
    return 1 if all_fails else 0


if __name__ == "__main__":
    sys.exit(main())
