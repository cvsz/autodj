"""Text-to-speech synthesis via pyttsx3 (Windows SAPI).

pyttsx3 uses COM STA on Windows and is NOT thread-safe: calling init() from
multiple threads concurrently corrupts COM state and causes random crashes or
silent failures.  All TTS work is therefore serialised through a dedicated
thread (_tts_thread) with a queue.  engine.speak() just submits jobs to that
queue; the thread processes them one at a time, so concurrent !speak commands
are queued rather than racing.
"""

from __future__ import annotations

import logging
import os
import queue
import threading
from collections.abc import Callable

log = logging.getLogger("autodj")

# ---- private TTS worker (one per process, started lazily) ------------------

_tts_queue: queue.Queue[Callable[[], None] | None] = queue.Queue()
_tts_started = False
_tts_lock = threading.Lock()
TTS_TIMEOUT = 60.0  # seconds a caller waits for one synthesis before giving up


def _worker():
    """Runs in a dedicated daemon thread; processes TTS jobs sequentially.

    Each job independently imports pyttsx3 inside its own try/except, so the
    worker stays alive even if pyttsx3 is not installed — every pending job
    gets its done event set (with the exception) rather than blocking forever.
    """
    while True:
        job = _tts_queue.get()
        if job is None:
            break
        try:
            job()
        except Exception:
            log.exception("TTS synthesis failed")


def _ensure_worker():
    global _tts_started
    with _tts_lock:
        if not _tts_started:
            t = threading.Thread(target=_worker, daemon=True, name="autodj-tts")
            t.start()
            _tts_started = True


# ---- public API ------------------------------------------------------------


def synth(text: str, path: str, cfg) -> None:
    """Synthesise *text* into a WAV file at *path* using the TTS worker thread.

    Blocks until the synthesis is complete (or fails).  Must NOT be called
    from the TTS worker thread itself (deadlock).
    """
    _ensure_worker()
    done = threading.Event()
    exc: list[Exception] = []

    def job():
        try:
            import pyttsx3

            eng = pyttsx3.init()
            eng.setProperty("rate", cfg.tts_rate)
            if cfg.tts_voice:
                for v in eng.getProperty("voices"):
                    if cfg.tts_voice.lower() in v.name.lower():
                        eng.setProperty("voice", v.id)
                        break
            eng.save_to_file(text, path)  # NOT inside the voice loop/if: with tts_voice = "" (the default) nothing was synthesised
            eng.runAndWait()
            if not os.path.isfile(path):
                raise RuntimeError("the TTS engine produced no audio file")
        except Exception as ex:
            exc.append(ex)
        finally:
            done.set()

    _tts_queue.put(job)
    if not done.wait(TTS_TIMEOUT):
        raise RuntimeError(f"text-to-speech did not finish within {TTS_TIMEOUT:.0f}s")
    if exc:
        raise exc[0]
