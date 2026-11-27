"""Shared pytest fixtures."""

from __future__ import annotations

import gc
import os
import shutil
from collections.abc import Iterator
from pathlib import Path

import pytest


def posix_bash() -> str | None:
    """Return a bash able to execute POSIX scripts with native Windows paths.

    On Windows, System32's ``bash.exe`` is the WSL launcher and cannot see a
    ``C:\\...`` script path, so only Git Bash is accepted there.
    """
    if os.name == "nt":
        for candidate in (
            r"C:\Program Files\Git\bin\bash.exe",
            r"C:\Program Files (x86)\Git\bin\bash.exe",
        ):
            if Path(candidate).is_file():
                return candidate
        return None
    return shutil.which("bash")


@pytest.fixture(autouse=True, scope="session")
def _private_cache_dir(tmp_path_factory: pytest.TempPathFactory) -> Iterator[None]:
    """Keep the library's metadata cache out of the real user cache folder."""
    old = os.environ.get("AUTODJ_CACHE_DIR")
    os.environ["AUTODJ_CACHE_DIR"] = str(tmp_path_factory.mktemp("autodj-cache"))
    yield
    if old is None:
        os.environ.pop("AUTODJ_CACHE_DIR", None)
    else:
        os.environ["AUTODJ_CACHE_DIR"] = old


@pytest.fixture(autouse=True)
def _collect_garbage_on_main_thread() -> Iterator[None]:
    """Finalise objects left over by a test on the main thread.

    Tk widgets that are still referenced when a GUI test returns (locals such as
    a settings window) are otherwise freed by whichever thread next triggers a
    garbage collection - e.g. a TestClient worker in the webhook tests. Tcl
    aborts the whole process ("Tcl_AsyncDelete: async handler deleted by the
    wrong thread") when its interpreter is torn down off the creating thread,
    which crashed the Linux CI run partway through the suite.
    """
    yield
    gc.collect()
