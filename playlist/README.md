# AutoDJ YouTube Genre Playlist Pack

This pack contains genre-separated JSON playlist files for `cvsz/autodj`.

## Files
Each `*.json` file follows the `version: 1` / `tracks: [...]` structure read by `camfrog_autodj/playlist.py`.
The pack includes Thai and international pop, rock, country, hip-hop, R&B, jazz, EDM, K-pop, J-pop, C-pop, classical, instrumental, ambient, workout, karaoke, and more.

## Converting the search entries to real YouTube URLs
In AutoDJ 0.2.5+, search queries (`ytsearch1:...`) are automatically resolved to verified YouTube URLs and titles on the fly and preloaded in the background without requiring offline resolution.

If you prefer to pre-resolve the entire playlist pack beforehand, you can run the optional offline resolution script on a machine with internet access:

```bash
python -m pip install -U yt-dlp
python resolve_urls.py --dry-run
python resolve_urls.py --report-json reports/playlist-resolution.json
```

The resolver automatically selects an explicit `--ytdlp` executable, a yt-dlp binary on PATH, or the current Python environment's `yt_dlp` module. TLS certificate verification is always enabled. POSIX systems, including WSL2, use the system CA store by default; Windows retains yt-dlp's normal CA behavior unless configured otherwise.

For a corporate HTTPS-inspection CA, export the trusted root/intermediate chain as a PEM bundle and pass it explicitly:

```bash
# WSL2/Linux: use the system trust store (also the default on POSIX)
python resolve_urls.py --system-ca --report-json reports/playlist-resolution.json

# Custom verified PEM bundle (Windows, WSL2, or Linux)
python resolve_urls.py --ca-bundle /path/to/trusted-ca-bundle.pem

# Or configure the path through the environment
export AUTODJ_YTDLP_CA_BUNDLE=/path/to/trusted-ca-bundle.pem
python resolve_urls.py
```

Do not use `--no-check-certificates` or otherwise disable TLS verification. The resolver retries only classified transient network failures (default: 2 retries with exponential backoff). Certificate verification failures and permanent HTTP errors are not retried. Tune this with `--retries 0..10` and `--retry-delay SECONDS`.

Each successful entry becomes `https://www.youtube.com/watch?v=<id>` with the video's real `title` and `duration`; the original search text is kept in `query`. The ID always comes from a live YouTube lookup, never a guess. A `.json.bak` copy of each file is made first, the script can be re-run (resumes, skips finished entries), and unresolved entries remain unchanged.

The console summary reports resolved/skipped/failed counts and the failure category. `--report-json PATH` writes a machine-readable report containing per-file totals and per-entry failure details. Exit codes: `0` all entries processed, `1` one or more playlist entries/files failed, `2` invalid tool/CA configuration or report output failure.

## How to use
1. Back up your existing `playlist.json`.
2. Copy one selected genre JSON to the AutoDJ working directory and set `playlist_file` in `config.toml` to that filename.
3. Restart AutoDJ and test with one track before enabling it for the room.

`playlist_file` is a single configured playlist store. These genre files are alternatives; the current app does not automatically merge all `*.json` files into one playlist.
The app may append requested tracks to the configured file, so keep a backup if you want the starter list unchanged.
