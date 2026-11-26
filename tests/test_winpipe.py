"""Named-pipe IPC with a real deadline, against a real Windows pipe server.

Live 2026-11-27 05:36-05:48: every song was logged "mpv did not answer ...
treating it as hung" 2 ms after the end check started (open() fails at once on
a busy pipe; read() blocks without a timeout) and counted as FAILED.
"""

from __future__ import annotations

import ctypes
import itertools
import os
import sys
import threading
import time

import pytest

pytestmark = pytest.mark.skipif(sys.platform != "win32", reason="Windows named pipes")

_n = itertools.count()


class PipeServer(threading.Thread):
    """One-instance byte pipe; each client gets `reply(request)` after `delay` s."""

    def __init__(self, reply, delay: float = 0.0, hold: float = 0.0, clients: int = 1):
        super().__init__(daemon=True)
        import ctypes.wintypes as w

        self.w = w
        self.k = ctypes.WinDLL("kernel32", use_last_error=True)
        self.k.CreateNamedPipeW.restype = w.HANDLE
        self.k.CreateNamedPipeW.argtypes = [
            w.LPCWSTR, w.DWORD, w.DWORD, w.DWORD, w.DWORD, w.DWORD, w.DWORD, ctypes.c_void_p,
        ]  # fmt: skip
        self.k.ConnectNamedPipe.argtypes = [w.HANDLE, ctypes.c_void_p]
        self.k.ReadFile.argtypes = [
            w.HANDLE,
            ctypes.c_void_p,
            w.DWORD,
            ctypes.POINTER(w.DWORD),
            ctypes.c_void_p,
        ]
        self.k.WriteFile.argtypes = [
            w.HANDLE,
            ctypes.c_void_p,
            w.DWORD,
            ctypes.POINTER(w.DWORD),
            ctypes.c_void_p,
        ]
        self.k.DisconnectNamedPipe.argtypes = [w.HANDLE]
        self.k.FlushFileBuffers.argtypes = [w.HANDLE]
        self.k.CloseHandle.argtypes = [w.HANDLE]
        self.name = rf"\\.\pipe\autodj-test-{os.getpid()}-{next(_n)}"
        self.reply, self.delay, self.hold, self.clients = reply, delay, hold, clients
        self.ready = threading.Event()
        self.requests: list[bytes] = []

    def run(self) -> None:
        for _ in range(self.clients):
            h = self.k.CreateNamedPipeW(self.name, 3, 0, 1, 65536, 65536, 0, None)
            self.ready.set()
            self.k.ConnectNamedPipe(h, None)
            buf = ctypes.create_string_buffer(4096)
            got = self.w.DWORD(0)
            self.k.ReadFile(h, buf, 4096, ctypes.byref(got), None)
            self.requests.append(buf.raw[: got.value])
            time.sleep(self.delay)
            out = self.reply(buf.raw[: got.value])
            if out:
                sent = self.w.DWORD(0)
                self.k.WriteFile(h, out, len(out), ctypes.byref(sent), None)
            self.k.FlushFileBuffers(h)  # wait until the client has read the reply
            time.sleep(self.hold)
            self.k.DisconnectNamedPipe(h)
            self.k.CloseHandle(h)


def _start(server: PipeServer) -> PipeServer:
    server.start()
    assert server.ready.wait(2)
    return server


def test_reply_is_read_after_mpv_event_lines():
    from autodj.winpipe import request

    s = _start(
        PipeServer(lambda r: b'{"event":"tick"}\n{"request_id":7,"data":12.5,"error":"success"}\n')
    )
    out = request(s.name, b'{"command":["get_property","time-pos"],"request_id":7}\n', 2.0,
                  lambda b: b'"request_id":7' in b)  # fmt: skip
    assert out is not None and b"12.5" in out
    s.join(2)


def test_busy_pipe_is_waited_for_instead_of_failing():
    """The GUI's poll holds the only instance for 0.3 s: the player's query still gets through."""
    from autodj.winpipe import request

    s = _start(PipeServer(lambda r: b'{"request_id":1,"data":1}\n', hold=0.3, clients=2))
    first = threading.Thread(target=request, args=(s.name, b"x\n", 2.0, lambda b: b"data" in b))
    first.start()
    time.sleep(0.05)  # the first client now owns the single instance
    t0 = time.monotonic()
    out = request(s.name, b"y\n", 2.0, lambda b: b"data" in b)
    assert out is not None and b'"data":1' in out
    assert time.monotonic() - t0 >= 0.2  # it waited for the instance
    first.join(2)
    s.join(3)


def test_silent_server_times_out_on_time():
    """A hung mpv that never answers: the call returns None within the timeout."""
    from autodj.winpipe import request

    s = _start(PipeServer(lambda r: b"", hold=2.0))
    t0 = time.monotonic()
    assert request(s.name, b"x\n", 0.3, lambda b: b"\n" in b) is None
    assert time.monotonic() - t0 < 1.0
    s.join(3)


def test_missing_pipe_raises_after_the_deadline():
    from autodj.winpipe import PipeError, request

    t0 = time.monotonic()
    with pytest.raises(PipeError):
        request(r"\\.\pipe\autodj-no-such-pipe", b"x\n", 0.2, lambda b: True)
    assert time.monotonic() - t0 < 1.0


def test_player_query_uses_the_real_pipe(tmp_path):
    """MpvPlayer._cmd_get end to end over a real pipe (the call the hang check makes)."""
    from autodj.config import Config
    from autodj.player import MpvPlayer

    def reply(req: bytes) -> bytes:
        rid = req.split(b'"request_id": ')[1].split(b"}")[0]
        return b'{"data": 201.4, "request_id": ' + rid + b', "error": "success"}\n'

    s = _start(PipeServer(reply))
    p = MpvPlayer(Config())
    p._ipc = s.name
    assert p._cmd_get("get_property", "time-pos", timeout=2.0) == pytest.approx(201.4)
    s.join(2)
