"""Concurrency tests for Phase 6 — Testing and Quality Engineering.

Covers: simultaneous queue modifications, concurrent command handling
with cooldown, duplicate events, and shutdown-during-playback safety.
"""

import json
import os
import tempfile
import threading
import time

from test_core import FakeAdapter, FakePlayer, T, make, out

from camfrog_autodj.adapters.base import ChatMessage
from camfrog_autodj.config import Config
from camfrog_autodj.engine import Engine
from camfrog_autodj.playqueue import PlayQueue

# ============================================================================
# PlayQueue concurrency
# ============================================================================


def test_concurrent_add_request_from_multiple_threads():
    """Multiple threads adding requests must not corrupt the queue."""
    q = PlayQueue(shuffle=False)
    errors = []

    def add_many(prefix, count):
        for i in range(count):
            q.add_request(T(f"{prefix}-{i}", prefix))

    threads = [threading.Thread(target=add_many, args=(f"t{n}", 50)) for n in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert not errors, errors
    assert len(q.requests) == 250  # 5 threads * 50 adds


def test_concurrent_add_and_pop():
    """Concurrent add and pop must not raise or lose items."""
    q = PlayQueue(shuffle=False)
    popped = []
    lock = threading.Lock()

    def adder():
        for i in range(100):
            q.add_request(T(f"add-{i}", "adder"))

    def popper():
        for _ in range(100):
            t = q.pop()
            if t is not None:
                with lock:
                    popped.append(t.title)

    threads = [threading.Thread(target=adder), threading.Thread(target=popper)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    total = len(q.requests) + len(popped)
    assert total == 100  # every added item is either still queued or popped


def test_remove_track_survives_concurrent_modification():
    """remove_track by identity must work while other threads mutate the queue."""
    q = PlayQueue(shuffle=False)
    tracks = [T(f"t{i}", "user") for i in range(20)]
    for t in tracks:
        q.add_request(t)

    target = tracks[10]

    def remover():
        q.remove_track(target)

    def mutator():
        for i in range(50):
            q.add_request(T(f"m{i}", "mutator"))

    threads = [threading.Thread(target=remover), threading.Thread(target=mutator)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert target not in q.requests

    # ============================================================================
    # Concurrent command handling + cooldown
    # ============================================================================
    """Concurrent commands from the same user must respect cooldown."""
    e = make()
    e.cfg.cooldown = 5.0
    results = []
    lock = threading.Lock()

    def fire_cmd(user, idx):
        e.router.handle(ChatMessage(user, f"!play song{idx}"))
        with lock:
            results.append(out(e))

    threads = [threading.Thread(target=fire_cmd, args=("amy", i)) for i in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    # With cooldown=5s and commands firing nearly simultaneously, only the
    # first should succeed; the rest should be dropped by cooldown.
    queued = [r for r in results if r and "Queued" in r[0]]
    assert len(queued) == 1, f"expected exactly 1 queued, got {len(queued)}: {results}"


def test_concurrent_commands_different_users():
    """Different users can each queue without blocking each other."""
    e = make()
    e.cfg.cooldown = 0
    results = []
    lock = threading.Lock()

    def fire_cmd(user, idx):
        e.router.handle(ChatMessage(user, f"!play song{idx}"))
        with lock:
            results.append(out(e))

    threads = [threading.Thread(target=fire_cmd, args=(f"user{i}", i)) for i in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    queued = [r for r in results if r and "Queued" in r[0]]
    assert len(queued) == 10, f"expected 10 queued, got {len(queued)}: {results}"


def test_duplicate_events_idempotent():
    """The same command delivered twice must not double-queue (dedup via already_queued)."""
    e = make()
    e.cfg.cooldown = 0
    e.router.handle(ChatMessage("amy", "!play unique-song"))
    out(e)
    # Same song again immediately — should be rejected as already queued
    e.router.handle(ChatMessage("amy", "!play unique-song"))
    assert "already in the queue" in out(e)[0]


# ============================================================================
# Shutdown during playback
# ============================================================================


def test_shutdown_joins_threads_with_timeout():
    """Engine.shutdown() must join all tracked threads within the timeout."""
    e = make()
    # Add a long-running thread to _threads to simulate an in-flight task
    stop_flag = threading.Event()

    def long_task():
        stop_flag.wait(30)

    t = threading.Thread(target=long_task, daemon=True, name="autodj-long-task")
    e._threads.append(t)
    t.start()
    assert len(e._threads) >= 1

    # Shutdown should not hang (5s timeout per thread)
    start = time.monotonic()
    e.shutdown()
    elapsed = time.monotonic() - start
    assert elapsed < 6, f"shutdown took {elapsed:.1f}s (should be < 6s)"
    stop_flag.set()


# ============================================================================
# Auto-reply loop concurrency with shutdown
# ============================================================================


def test_auto_reply_loop_stops_on_shutdown():
    """The auto-reply loop thread must exit when stop_evt is set."""
    tmp = tempfile.mkdtemp()
    ads = os.path.join(tmp, "ads-list.json")
    with open(ads, "w", encoding="utf-8") as f:
        json.dump({"messages": ["msg one", "msg two"]}, f)

    cfg = Config(auto_reply_enabled=True, auto_reply_interval=60.0, auto_reply_file=ads)
    e = Engine(cfg, FakeAdapter(), player=FakePlayer(), index=None)
    e.cfg_path = os.path.join(tmp, "config.toml")

    start = time.monotonic()
    # Run loop briefly, then stop
    loop_thread = threading.Thread(target=e._auto_reply_loop, daemon=True)
    loop_thread.start()
    time.sleep(0.1)
    e.stop_evt.set()
    loop_thread.join(timeout=5)
    elapsed = time.monotonic() - start

    assert not loop_thread.is_alive(), "auto-reply loop did not stop on shutdown"
    assert elapsed < 6, f"loop did not exit promptly ({elapsed:.1f}s)"
