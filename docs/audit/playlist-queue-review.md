# Playlist and Queue Review — cvsz/autodj

Audited: `camfrog_autodj/playlist.py`, `playqueue.py`, and `engine.py` playlist/queue handling.

## Playlist (`playlist.json`)

- **Format:** `{"version":1,"tracks":[{"source","title","duration","added_by","added"}]}` — human-editable JSON.
- **Loading:** `load_playlist` — missing or corrupt file → `[]` (logged, never fatal). Invalid sources skipped with warning. Malformed JSON → `[]`, file **not** overwritten.
- **Saving:** `save_playlist` — atomic (tmp file + `os.replace`); `.bak` backup before write via `PlaylistStore.add`/discover.
- **Unreadable file handling:** `.corrupt-<timestamp>` backup preserved; load continues with `[]`.
- **Dedup:** by `source` in `PlaylistStore.add` and `PlayQueue.add_pool`.
- **Backward compatibility:** reads `version:1` shape; tolerates missing fields (`duration`, `added_by`, `added`).

## PlayQueue (`playqueue.py`)

- **Ordering:** requests first, then autoplay pool (looping). `peek()` stable until `pop()`.
- **Shuffle / repeat:** `shuffle` bool; `repeat` = `off` | `one`. Shuffle excludes last track when possible.
- **next/previous:** `pop()` removes head of requests (or next auto from pool).
- **Current track:** `Engine.current`; `position()` from mpv IPC or wall-clock fallback (pauses excluded).
- **Missing files:** not pre-checked; mpv failure handled by backoff (max 3 announcements, then backoff 1,2,4…30s).
- **Queue persistence:** `playlist.json` persists requests; queue/volume/shuffle repeat are runtime-only (documented by design).
- **Concurrent updates:** `RLock` guards all mutations; `PlaylistStore` has its own lock.
- **Duplicate prevention:** `_assert_not_already_queued` checks `e.current` and `e.queue.requests` under lock; `remove_track` by identity survives queue shifts.

## Tests (critical regression areas)

Covered by `test_hardening.py`, `test_core.py`, `test_playlist_resolver.py`, `test_installer_data_safety.py`:
- Empty playlist, malformed JSON, missing playlist → `[]`
- Duplicate entries → rejected for non-admins
- Unicode paths → handled by `Path`
- Deleted tracks → not pre-checked (mpv failure path)
- Concurrent save → lock-protected
- Interrupted save → atomic tmp+replace
- Application restart → playlist.json reloaded at startup

## Atomic file replacement

All persistent writes use tmp + `os.replace` (atomic on same volume) with `.bak` backup. No silent deletion of invalid entries without backup; `PlaylistStore.add` backs up unreadable files as `.corrupt-<ts>`.

## Conclusion

Playlist integrity verified; atomic writes; backward compatible; concurrency protected. No confirmed defects.
