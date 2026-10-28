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
import queue
import threading
from typing import Callable

log = logging.getLogger("autodj")

# ---- private TTS worker (one per process, started lazily) ------------------

_tts_queue: queue.Queue[Callable[[], None] | None] = queue.Queue()
_tts_started = False
_tts_lock = threading.Lock()


def _worker():
    """Runs in a dedicated daemon thread; keeps a single pyttsx3 engine alive."""
    try:
        import pyttsx3
        _eng = pyttsx3.init()
    except Exception:
        log.exception("pyttsx3 failed to initialise; TTS is disabled")
        # drain the queue so callers don't block
        while True:
            job = _tts_queue.get()
            if job is None:
                break
        return
    while True:
        job = _tts_queue.get()
        if job is None:
            break
        try:
            job(_eng)
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

    def job(eng):
        try:
            eng.setProperty("rate", cfg.tts_rate)
            if cfg.tts_voice:
                for v in eng.getProperty("voices"):
                    if cfg.tts_voice.lower() in v.name.lower():
                        eng.setProperty("voice", v.id)
                        break
            eng.save_to_file(text, path)
            eng.runAndWait()
        except Exception as ex:
            exc.append(ex)
        finally:
            done.set()

    _tts_queue.put(job)
    done.wait()
    if exc:
        raise exc[0]

