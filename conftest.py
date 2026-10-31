"""pytest configuration and monkey-patches for CI compatibility."""

import os
import sys

_HOST_OS_NAME = os.name

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

            get_verbosity = getattr(self.config, "get_verbosity", None)
            verbosity = (
                get_verbosity()
                if callable(get_verbosity)
                else self.config.getoption("verbose", 0)
            )
            truncate_locals = verbosity <= 1

            # FIX: Use os.path instead of pathlib.Path to avoid cross-platform issues
            # Always use abspath=True to avoid the problematic comparison
            abspath = True

            previous_os_name = os.name
            try:
                # Tests may temporarily simulate Windows by patching os.name. Restore
                # the host platform while pytest resolves traceback paths.
                os.name = _HOST_OS_NAME
                return excinfo.getrepr(
                    funcargs=True,
                    abspath=abspath,
                    showlocals=self.config.getoption("showlocals", False),
                    style=style,
                    tbfilter=tbfilter,
                    truncate_locals=truncate_locals,
                )
            finally:
                os.name = previous_os_name

        _pytest.nodes.Node._repr_failure_py = patched_repr_failure_py
    except Exception:
        # If patching fails, continue without it
        pass


def pytest_sessionfinish(session, exitstatus):
    """Disable cache provider on Python 3.11 to avoid cross-platform path issues."""
    if sys.version_info >= (3, 11) and sys.version_info < (3, 12):
        # The cache provider is already disabled via -p no:cacheprovider
        pass