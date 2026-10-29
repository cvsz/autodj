from __future__ import annotations

import os
import sys

import pytest
from _pytest.outcomes import fail


def test_failure_renderer_handles_pytest_fail_exception(request):
    """The Python 3.11 compatibility renderer must not mask pytest.fail."""
    try:
        fail("rendered without an internal error", pytrace=False)
    except fail.Exception as exc:
        excinfo = pytest.ExceptionInfo.from_exception(exc)

    with pytest.MonkeyPatch.context() as patch:
        if sys.version_info[:2] == (3, 11) and os.name != "nt":
            patch.setattr(os, "name", "nt")
        rendered = request.node._repr_failure_py(excinfo, style="auto")

    assert rendered is not None
