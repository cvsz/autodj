"""Tie child processes (mpv) to AutoDJ's lifetime on Windows.

A Windows Job Object created with JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE kills
every process in it when its last handle closes, and the OS closes our handle
when AutoDJ exits for *any* reason: normal close, crash, Task Manager
"End task" or ``taskkill /F``.  Without it, a force-closed AutoDJ left mpv.exe
playing in the background with nothing able to stop it.

Only processes passed to :func:`kill_with_parent` join the job (mpv, and the
yt-dlp it starts).  AutoDJ itself does not: Camfrog started by ``auto_launch``
and the updater's installer must outlive AutoDJ.

Everything here is best-effort: failures are logged at debug level and never
stop playback.  On other platforms it is a no-op.
"""

from __future__ import annotations

import ctypes
import logging
import subprocess  # nosec B404 - only used for type hints of existing Popen objects
import sys
import threading

log = logging.getLogger("autodj")

_JOB_OBJECT_EXTENDED_LIMIT_INFORMATION = 9
_JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE = 0x2000

_job: int | None = None
_job_failed = False
_lock = threading.Lock()


def _structs():
    from ctypes import wintypes

    class IoCounters(ctypes.Structure):
        _fields_ = [
            (name, ctypes.c_ulonglong)
            for name in (
                "ReadOperationCount",
                "WriteOperationCount",
                "OtherOperationCount",
                "ReadTransferCount",
                "WriteTransferCount",
                "OtherTransferCount",
            )
        ]

    class JobBasicLimitInfo(ctypes.Structure):
        _fields_ = [
            ("PerProcessUserTimeLimit", ctypes.c_int64),
            ("PerJobUserTimeLimit", ctypes.c_int64),
            ("LimitFlags", wintypes.DWORD),
            ("MinimumWorkingSetSize", ctypes.c_size_t),
            ("MaximumWorkingSetSize", ctypes.c_size_t),
            ("ActiveProcessLimit", wintypes.DWORD),
            ("Affinity", ctypes.c_size_t),
            ("PriorityClass", wintypes.DWORD),
            ("SchedulingClass", wintypes.DWORD),
        ]

    class JobExtendedLimitInfo(ctypes.Structure):
        _fields_ = [
            ("BasicLimitInformation", JobBasicLimitInfo),
            ("IoInfo", IoCounters),
            ("ProcessMemoryLimit", ctypes.c_size_t),
            ("JobMemoryLimit", ctypes.c_size_t),
            ("PeakProcessMemoryUsed", ctypes.c_size_t),
            ("PeakJobMemoryUsed", ctypes.c_size_t),
        ]

    return JobExtendedLimitInfo


def _kernel32():
    from ctypes import wintypes

    k32 = ctypes.WinDLL("kernel32", use_last_error=True)  # type: ignore[attr-defined]
    k32.CreateJobObjectW.argtypes = (ctypes.c_void_p, wintypes.LPCWSTR)
    k32.CreateJobObjectW.restype = wintypes.HANDLE
    k32.SetInformationJobObject.argtypes = (
        wintypes.HANDLE,
        ctypes.c_int,
        ctypes.c_void_p,
        wintypes.DWORD,
    )
    k32.SetInformationJobObject.restype = wintypes.BOOL
    k32.AssignProcessToJobObject.argtypes = (wintypes.HANDLE, wintypes.HANDLE)
    k32.AssignProcessToJobObject.restype = wintypes.BOOL
    return k32


def _get_job() -> int | None:
    """The process-wide kill-on-close job, created on first use (None if unavailable)."""
    global _job, _job_failed
    with _lock:
        if _job is not None or _job_failed:
            return _job
        try:
            k32 = _kernel32()
            job = k32.CreateJobObjectW(None, None)
            if not job:
                raise OSError(ctypes.get_last_error(), "CreateJobObjectW failed")  # type: ignore[attr-defined]
            info = _structs()()
            info.BasicLimitInformation.LimitFlags = _JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
            if not k32.SetInformationJobObject(
                job,
                _JOB_OBJECT_EXTENDED_LIMIT_INFORMATION,
                ctypes.byref(info),
                ctypes.sizeof(info),
            ):
                raise OSError(ctypes.get_last_error(), "SetInformationJobObject failed")  # type: ignore[attr-defined]
            _job = int(job)  # never closed: the OS closes it when AutoDJ exits
        except (OSError, AttributeError, ValueError) as ex:
            _job_failed = True
            log.debug("kill-on-close job unavailable: %s", ex)
        return _job


def kill_with_parent(proc: subprocess.Popen) -> bool:
    """Make *proc* (and the children it starts later) die when AutoDJ exits.

    Returns True if the process was attached.  No-op (False) off Windows or when
    the job cannot be created; never raises.
    """
    if sys.platform != "win32":
        return False
    handle = getattr(proc, "_handle", None)  # CPython's Windows Popen keeps the process handle
    job = _get_job()
    if not handle or job is None:
        return False
    try:
        if _kernel32().AssignProcessToJobObject(job, int(handle)):
            return True
        log.debug(
            "could not tie pid %s to AutoDJ's lifetime (error %s)",
            proc.pid,
            ctypes.get_last_error(),  # type: ignore[attr-defined]
        )
    except (OSError, AttributeError, ValueError) as ex:
        log.debug("could not tie pid %s to AutoDJ's lifetime: %s", proc.pid, ex)
    return False
