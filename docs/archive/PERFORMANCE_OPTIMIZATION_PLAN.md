# Performance Optimization Plan for CamfrogAutoDJ

## Current Architecture Analysis

The application consists of:
- **Engine**: Multi-threaded core with 6 daemon threads (sender, player_loop, load_all, chat_loop, auto_reply_loop, im_auto_reply_loop)
- **GUI**: Tkinter-based with 30fps animation + 500ms data polling
- **Player**: mpv subprocess per track with JSON IPC (named pipe/Unix socket)
- **Library**: Recursive folder scanning with symlink protection
- **Queue**: Thread-safe with version counter for change detection

## Identified Performance Bottlenecks

### 1. Lock Contention (HIGH IMPACT)
- `_chat_lock` guards `chat_log`, `chat_seq`, `im_log`, `im_seq`, `_im_reply_cooldowns`
- `_send_failure_lock` guards circuit breaker + send failures (reused for different purposes)
- `_chat_rate_lock` guards per-nick rate limiting
- `queue.lock` (RLock) guards all queue operations
- Operations often acquire multiple locks sequentially

### 2. IPC Connection Overhead (HIGH IMPACT)
- `get_time_pos()` opens/closes IPC connection every call (cached 0.5s)
- Each seek/pause/volume/resume opens new connection
- Windows named pipes have higher overhead than Unix sockets

### 3. GUI Rendering Overhead (MEDIUM IMPACT)
- 30fps animation loop redraws: record spin, equalizer bars, particles, confetti, border glow
- Canvas operations are relatively expensive in Tkinter
- Full redraw on every frame even when minimal changes

### 4. Thread Wakeup Frequency (MEDIUM IMPACT)
- `poll_interval` default 0.5s for chat reads
- `sender` wakes every 0.5s + send_interval
- `auto_reply_loop` wakes every interval (default 300s)
- `im_auto_reply_loop` wakes every 60s for cleanup
- `player_loop` wakes every 0.5s (POLL) for hang detection

### 5. Library Scanning (LOW IMPACT - only at startup)
- Recursive single-threaded scanning
- `mutagen` metadata extraction per file
- Symlink checks on every entry

### 6. Command Rate Limiting Cleanup (LOW IMPACT)
- `_within_limits` prunes expired entries on EVERY command
- Iterates all users' request lists and cooldown entries

## Optimization Plan

### Phase 1: Core Engine Optimizations (High Impact, Low Risk)

1. **Persistent IPC Connection for mpv**
   - Keep IPC connection open during track playback
   - Reuse for get_time_pos, seek, pause, volume, resume
   - Only close when track ends or mpv dies

2. **Separate Locks for Distinct Resources**
   - Split `_send_failure_lock` into dedicated locks for circuit breaker vs send failures
   - Use `threading.Lock` instead of `RLock` where reentrancy not needed
   - Consider `threading.RLock` only for queue (already used correctly)

3. **Batch Rate Limit Cleanup**
   - Move cleanup to dedicated periodic task (every 60s)
   - Avoid O(N) scan on every command

4. **Optimize Engine Generation Counter**
   - Already well-designed; ensure minimal bumping

### Phase 2: GUI Optimizations (Medium Impact)

5. **Reduce Animation Redraw Overhead**
   - Cache static elements (record, equalizer background)
   - Only redraw changing elements (bar heights, particle positions)
   - Use `after_idle` for non-critical updates

6. **Optimize Canvas Operations**
   - Batch canvas updates
   - Avoid unnecessary coordinate calculations

7. **Adaptive Polling**
   - Reduce GUI data poll frequency when idle (no track playing)
   - Increase when actively playing

### Phase 3: Library/Startup Optimizations (Low Impact)

8. **Parallel Directory Scanning**
   - Use ThreadPoolExecutor for parallel subdirectory scanning
   - Respect `max_dirs` and `limit` budgets

9. **Metadata Caching**
   - Cache mutagen results in index file
   - Skip re-scanning unchanged files (mtime check)

### Phase 4: Advanced Optimizations (Higher Risk)

10. **Async/Await for I/O Bound Operations**
    - Consider migrating to asyncio for chat/player/sender loops
    - Would require significant refactor

11. **Connection Pooling for yt-dlp**
    - Reuse yt-dlp processes for multiple queries
    - Currently spawns new process per lookup

## Implementation Priority

| Priority | Optimization | Est. Impact | Risk |
|----------|-------------|-------------|------|
| 1 | Persistent IPC Connection | High (reduces IPC overhead 10x) | Low |
| 2 | Separate Locks | High (reduces contention) | Low |
| 3 | Batch Rate Limit Cleanup | Medium | Low |
| 4 | Adaptive GUI Polling | Medium | Low |
| 5 | Optimized Animation Rendering | Medium | Medium |
| 6 | Parallel Library Scan | Low (startup only) | Low |
| 7 | Metadata Caching | Low | Medium |

## Success Metrics

- Reduce CPU usage during idle by >30%
- Reduce GUI frame time from ~16ms to <8ms
- Reduce IPC latency for position queries from ~5ms to <0.5ms
- Reduce lock contention wait times
- Maintain all 448 tests passing

## Validation Strategy

1. Run existing test suite after each change
2. Profile with `cProfile` before/after
3. Measure GUI frame times
4. Verify no regressions in functionality