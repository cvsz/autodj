"""A chat control that is not there yet must be retried, not crash the chat loop."""

from types import SimpleNamespace

import pytest

from autodj.adapters.uia import UiaAdapter


def _adapter(controls):
    a = UiaAdapter.__new__(UiaAdapter)  # no Camfrog / pywinauto needed
    a.win = SimpleNamespace(descendants=lambda control_type: controls)
    return a


def test_missing_control_raises_runtime_error_for_retry():
    with pytest.raises(RuntimeError, match="not found"):
        _adapter([])._find("Document", 0)


def test_present_control_is_returned():
    assert _adapter(["a", "b"])._find("Document", 1) == "b"
    assert _adapter(["a", "b"])._find("Document", -1) == "b"


def test_keys_literal_escapes_send_keys_specials():
    from autodj.adapters.uia import _keys_literal

    assert _keys_literal("a+b (c) {d} ^%~ [x]") == "a{+}b {(}c{)} {{}d{}} {^}{%}{~} {[}x{]}"
    assert _keys_literal("line1\nline2") == "line1 line2"
    assert _keys_literal("กร camfrog:join:ZeaZDev") == "กร camfrog:join:ZeaZDev"
