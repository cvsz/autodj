"""pytest configuration and monkey-patches for CI compatibility."""

import os
import sys


def pytest_configure(config):
    """Monkey-patch pytest's _repr_failure_py to handle cross-platform path issues on Py3.11."""
    if sys.version_info >= (3, 11) and sys.version_info < (3, 12):
        # Patch the problematic method in _pytest.nodes.Node
        import _pytest.nodes

        original_repr_failure_py = _pytest.nodes.Node._repr_failure_py

        def patched_repr_failure_py(self, excinfo, style=None):
            from _pytest.fixtures import FixtureLookupError
            from _pytest._code import TerminalRepr
            from _pytest import fail

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
            try:
                cwd = os.getcwd()
                inv_dir = self.config.invocation_params.dir
                # Normalize both paths for comparison
                abspath = os.path.normcase(os.path.abspath(cwd)) != os.path.normcase(os.path.abspath(inv_dir))
            except OSError:
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


def pytest_sessionfinish(session, exitstatus):
    """Disable cache provider on Python 3.11 to avoid cross-platform path issues."""
    if sys.version_info >= (3, 11) and sys.version_info < (3, 12):
        # The cache provider is already disabled via -p no:cacheprovider
        pass