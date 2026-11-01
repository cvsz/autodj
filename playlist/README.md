# AutoDJ YouTube Genre Playlist Pack

This pack contains genre-separated JSON playlist files for `cvsz/autodj`.

## Files
Each `*.json` file follows the `version: 1` / `tracks: [...]` structure read by `camfrog_autodj/playlist.py`.
The pack includes Thai and international pop, rock, country, hip-hop, R&B, jazz, EDM, K-pop, J-pop, C-pop, classical, instrumental, ambient, workout, karaoke, and more.

## Converting the search entries to real YouTube URLs
In AutoDJ 0.2.5+, search queries (`ytsearch1:...`) are automatically resolved to verified YouTube URLs and titles on the fly and preloaded in the background without requiring offline resolution.

If you prefer to pre-resolve the entire playlist pack beforehand, you can run the optional offline resolution script on a machine with internet access:

```
pip install yt-dlp
python resolve_urls.py --dry-run     # preview, writes nothing
python resolve_urls.py               # fix every *.json in this folder
```

Each entry becomes `https://www.youtube.com/watch?v=<id>` with the video's real `title` and `duration`; the original search text is kept in `query`. The ID always comes from a live YouTube lookup, never a guess. A `.json.bak` copy of each file is made first, the script can be re-run (resumes, skips finished entries), and entries with no playable result are left unchanged and listed at the end (exit code 1).

## How to use
1. Back up your existing `playlist.json`.
2. Copy one selected genre JSON to the AutoDJ working directory and set `playlist_file` in `config.toml` to that filename.
3. Restart AutoDJ and test with one track before enabling it for the room.

`playlist_file` is a single configured playlist store. These genre files are alternatives; the current app does not automatically merge all `*.json` files into one playlist.
The app may append requested tracks to the configured file, so keep a backup if you want the starter list unchanged.
