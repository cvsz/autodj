# Playlist and Queue Review — CamfrogAutoDJ

**Repository:** github.com/cvsz/autodj  
**Baseline SHA:** `fb5e99a`  
**Status:** Reviewed and tested

## Playlist persistence (`playlist.py`)

- Format: `{"version": 1, "tracks": [{source, title, duration, added_by, added}]}`.
- `load_playlist`: missing file → `[]`; corrupt/unreadable → logged warning, `[]`, **never overwritten**.
- Corrupt file recovery: `PlaylistStore.add` backs up the unreadable file as `playlist.corrupt-<timestamp>` before replacing.
- `save_playlist`: atomic write via `<path>.tmp` + `Path.replace` (same-filesystem atomic); guarded by `PlaylistStore.lock`.
- `PlaylistStore.add`: dedup by `source`, appends with `added` timestamp, never breaks the request on write failure.
- `update_source`: replaces a track after ytsearch → real URL resolution.

## Play queue (`playqueue.py`)

- Requests first, then autoplay pool (looping). `peek()` stable until `pop()`.
- Thread-safe via `threading.RLock`; `add_request`, `add_pool` (dedup), `remove`, `remove_track` (by identity), `clear`, `count_by`, `get`.
- Shuffle avoids immediate repeat of the last track (`random.choice`, not security-sensitive).
- Repeat: `off | one`.

## Commands (`commands.py`)

- `!play`/`!np`/`!next`/`!queue`/`!history`/`!voteskip`/`!remove`/`!help` (everyone); `!skip`/`!pause`/`!resume`/`!vol`/`!shuffle`/`!repeat`/`!clear`/`!load`/`!say`/`!speak`/`!block`/`!unblock` (admin).
- Non-admin limits: YouTube-only, 1 track, `max_duration`, no live, `max_requests_per_user`, sliding window `rate_limit_window`, cooldown, duplicate-request refusal.
- Rate limit and cooldown are per-user (case-insensitive).

## Findings

No defects found. Corrupt-file backup, atomic save, dedup, and rate limiting are all covered by `tests/test_play_flow.py` and `tests/test_hardening.py`.

## Verdict

Playlist integrity and queue behavior are verified by tests on Linux. No code change needed.
