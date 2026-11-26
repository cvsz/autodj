"""Stream modules log their warnings and errors.

They used to define ``_LOG = None  # placeholder for injected logging`` and guard
every call with ``if _LOG:``; nothing ever injected a logger, so every streaming
warning (adapter skipped: api_key missing, connect/send failures) was dropped.
"""

from __future__ import annotations

import importlib
import io
import logging
from types import SimpleNamespace

import pytest

from autodj.stream.adapter_manager import AdapterManager
from autodj.textutil import safe_print

MODULES = [
    "autodj.stream.adapter_manager",
    "autodj.stream.adapters.composite",
    "autodj.stream.transcoder",
    "autodj.stream.adapters.tiktok",
    "autodj.stream.adapters.facebook",
    "autodj.stream.adapters.youtube",
]


@pytest.mark.parametrize("name", MODULES)
def test_module_has_a_real_logger(name):
    mod = importlib.import_module(name)
    assert isinstance(mod._LOG, logging.Logger)
    assert mod._LOG.name == "autodj.stream"


def test_skipped_adapter_is_logged(caplog):
    mgr = AdapterManager.__new__(AdapterManager)
    with caplog.at_level(logging.WARNING, logger="autodj.stream"):
        assert mgr._make_youtube({}, "s1", {}) is None
    assert "youtube adapter skipped: api_key missing" in caplog.text


def test_safe_print_without_a_console_is_a_no_op(monkeypatch):
    monkeypatch.setattr("sys.stdout", None)
    safe_print("ข้อความ")  # windowed exe: sys.stdout is None -> nothing, no crash
    buf = io.StringIO()
    safe_print("ok", file=buf)
    assert buf.getvalue() == "ok\n"


def test_composite_pump_logs_a_crashing_adapter(caplog):
    from autodj.stream.adapters.composite import CompositeStreamAdapter

    class Boom:
        def messages(self):
            raise RuntimeError("socket closed")

    c = CompositeStreamAdapter.__new__(CompositeStreamAdapter)
    c._stop = SimpleNamespace(is_set=lambda: False)
    with caplog.at_level(logging.WARNING, logger="autodj.stream"):
        c._pump("youtube", Boom())  # must not raise: the reader thread survives
    assert "adapter youtube message loop stopped" in caplog.text
