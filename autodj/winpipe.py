"""Windows named-pipe request/reply with a real deadline (mpv JSON IPC).

``open(r"\\\\.\\pipe\\x", "r+b")`` fails at once when every pipe instance is busy
(the GUI polls mpv's position over the same pipe every 0.5 s) and its ``read()``
blocks with no timeout. Live 2026-11-27 05:36-05:48 every song was logged
``mpv did not answer ... treating it as hung`` 2 ms after the check started and
counted as FAILED. Here the connect waits for a free instance (``WaitNamedPipeW``)
and the read polls ``PeekNamedPipe``, so *timeout* bounds the whole exchange.
"""

from __future__ import annotations

import ctypes
import errno
import time
from collections.abc import Callable

_GENERIC_READ = 0x80000000
_GENERIC_WRITE = 0x40000000
_OPEN_EXISTING = 3
_INVALID_HANDLE = ctypes.c_void_p(-1).value
_ERROR_FILE_NOT_FOUND = 2
_ERROR_PIPE_BUSY = 231
_ERROR_BROKEN_PIPE = 109
_ERROR_PIPE_NOT_CONNECTED = 233
_POLL_S = 0.01


class PipeError(OSError):
    """The pipe could not be opened, written or read."""


def _kernel32():
    win_dll = getattr(ctypes, "WinDLL", None)
    if win_dll is None:  # not Windows: an OSError like any other unreachable pipe
        raise PipeError(errno.ENOSYS, "named pipes need Windows")
    import ctypes.wintypes as w

    k = win_dll("kernel32", use_last_error=True)
    k.CreateFileW.argtypes = [
        w.LPCWSTR, w.DWORD, w.DWORD, ctypes.c_void_p, w.DWORD, w.DWORD, w.HANDLE,
    ]  # fmt: skip
    k.CreateFileW.restype = w.HANDLE
    k.WaitNamedPipeW.argtypes = [w.LPCWSTR, w.DWORD]
    k.WaitNamedPipeW.restype = w.BOOL
    k.WriteFile.argtypes = [
        w.HANDLE,
        ctypes.c_void_p,
        w.DWORD,
        ctypes.POINTER(w.DWORD),
        ctypes.c_void_p,
    ]
    k.WriteFile.restype = w.BOOL
    k.ReadFile.argtypes = [
        w.HANDLE,
        ctypes.c_void_p,
        w.DWORD,
        ctypes.POINTER(w.DWORD),
        ctypes.c_void_p,
    ]
    k.ReadFile.restype = w.BOOL
    k.PeekNamedPipe.argtypes = [
        w.HANDLE, ctypes.c_void_p, w.DWORD, ctypes.c_void_p, ctypes.POINTER(w.DWORD), ctypes.c_void_p,
    ]  # fmt: skip
    k.PeekNamedPipe.restype = w.BOOL
    k.CloseHandle.argtypes = [w.HANDLE]
    k.CloseHandle.restype = w.BOOL
    return k, w


def _connect(k, name: str, deadline: float):
    """Open *name*, waiting for a free pipe instance until *deadline*."""
    while True:
        h = k.CreateFileW(name, _GENERIC_READ | _GENERIC_WRITE, 0, None, _OPEN_EXISTING, 0, None)
        if h not in (None, _INVALID_HANDLE):
            return h
        err = ctypes.get_last_error()  # type: ignore[attr-defined]  # Windows only
        left_ms = int((deadline - time.monotonic()) * 1000)
        if left_ms <= 0 or err not in (_ERROR_PIPE_BUSY, _ERROR_FILE_NOT_FOUND):
            raise PipeError(err, f"cannot open {name}")
        if err == _ERROR_PIPE_BUSY:
            k.WaitNamedPipeW(name, max(1, min(left_ms, 200)))
        else:  # mpv has not created the pipe yet (just started)
            time.sleep(min(0.05, left_ms / 1000))


def request(name: str, data: bytes, timeout: float, done: Callable[[bytes], bool]) -> bytes | None:
    """Send *data* to pipe *name*; read until ``done(buffer)`` or *timeout* seconds.

    Returns the bytes read (``None`` when the deadline passed first). Raises
    PipeError when the pipe cannot be opened or written.
    """
    k, w = _kernel32()
    deadline = time.monotonic() + max(0.0, timeout)
    h = _connect(k, name, deadline)
    try:
        written = w.DWORD(0)
        buf = ctypes.create_string_buffer(data, len(data))
        if not k.WriteFile(h, buf, len(data), ctypes.byref(written), None):
            raise PipeError(ctypes.get_last_error(), f"cannot write {name}")  # type: ignore[attr-defined]
        response = b""
        avail = w.DWORD(0)
        while not done(response):
            if not k.PeekNamedPipe(h, None, 0, None, ctypes.byref(avail), None):
                err = ctypes.get_last_error()  # type: ignore[attr-defined]  # Windows only
                if err in (_ERROR_BROKEN_PIPE, _ERROR_PIPE_NOT_CONNECTED):
                    return response  # mpv closed the pipe (exited)
                raise PipeError(err, f"cannot read {name}")
            if avail.value:
                chunk = ctypes.create_string_buffer(avail.value)
                got = w.DWORD(0)
                if not k.ReadFile(h, chunk, avail.value, ctypes.byref(got), None):
                    raise PipeError(ctypes.get_last_error(), f"cannot read {name}")  # type: ignore[attr-defined]
                response += chunk.raw[: got.value]
                continue
            if time.monotonic() >= deadline:
                return None
            time.sleep(_POLL_S)
        return response
    finally:
        k.CloseHandle(h)
