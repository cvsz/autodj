"""Shared pytest fixtures."""

from __future__ import annotations

import gc
from collections.abc import Iterator

import pytest


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
