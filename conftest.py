"""pytest configuration and monkey-patches for CI compatibility."""

import os
import sys

# Monkey-patch pytest's _repr_failure_py at import time to handle cross-platform path issues on Py3.11
if sys.version_info >= (3, 11) and sys.version_info < (3, 12):
    try:
        import _pytest.nodes

        def patched_repr_failure_py(self, excinfo, style=None):
            # Completely replace the method to avoid Path() call that fails on cross-platform paths
            from _pytest.fixtures import FixtureLookupError
            from _pytest.outcomes import fail

            if isinstance(excinfo.value, _pytest.nodes.ConftestImportFailure):
                excinfo = _pytest.ExceptionInfo.from_exception(excinfo.value.cause)
            if isinstance(excinfo.value, fail.Exception):
                if not excinfo.value.pytrace:
                    style = "value"
            if isinstance(excinfo.value, FixtureLookupError):
                return excinfo.value.formatrepr()

            tbfilter = None
            if self.config.getoption("fulltrace", False):
                style = "long"
                tbfilter = False
            else:
                tbfilter = self._traceback_filter
                if style == "auto":
                    style = "long"

            if self.config.get_verbosity() > 1:
                truncate_locals = False
            else:
                truncate_locals = True

            truncate_args = False if self.config.get_verbosity() > 2 else True

            # FIX: Use os.path instead of pathlib.Path to avoid cross-platform issues
            # Always use abspath=True to avoid the problematic comparison
            abspath = True

            return excinfo.getrepr(
                funcargs=True,
                abspath=abspath,
                showlocals=self.config.getoption("showlocals", False),
                style=style,
                tbfilter=tbfilter,
                truncate_locals=truncate_locals,
                truncate_args=truncate_args,
            )

        _pytest.nodes.Node._repr_failure_py = patched_repr_failure_py
    except Exception:
        # If patching fails, continue without it
        pass


def pytest_sessionfinish(session, exitstatus):
    """Disable cache provider on Python 3.11 to avoid cross-platform path issues."""
    if sys.version_info >= (3, 11) and sys.version_info < (3, 12):
        # The cache provider is already disabled via -p no:cacheprovider
        pass