"""pytest configuration and monkey-patches for CI compatibility."""

import os
import pathlib
import sys


def pytest_configure(config):
    """Monkey-patch pytest's _repr_failure_py to handle cross-platform path issues on Py3.11."""
    if sys.version_info >= (3, 11) and sys.version_info < (3, 12):
        # Patch the problematic method in _pytest.nodes.Node
        import _pytest.nodes

        original_repr_failure_py = _pytest.nodes.Node._repr_failure_py

        def patched_repr_failure_py(self, excinfo, style=None):
            try:
                return original_repr_failure_py(self, excinfo, style)
            except NotImplementedError as e:
                if "cannot instantiate" in str(e) and ("WindowsPath" in str(e) or "PosixPath" in str(e)):
                    # Workaround: use os.path for comparison instead of pathlib.Path
                    cwd = os.getcwd()
                    inv_dir = self.config.invocation_params.dir
                    # Normalize both paths for comparison
                    abspath = os.path.normcase(os.path.abspath(cwd)) != os.path.normcase(os.path.abspath(inv_dir))
                    # Call the original method but with our workaround
                    # We need to replicate the logic but avoid the Path() call
                    from _pytest.nodes import Item
                    if isinstance(self, Item):
                        return self._repr_failure_py_impl(excinfo, style, abspath)
                raise

        _pytest.nodes.Node._repr_failure_py = patched_repr_failure_py


# Also patch the cache provider to avoid WindowsPath/PosixPath issues
def pytest_sessionfinish(session, exitstatus):
    """Disable cache provider on Python 3.11 to avoid cross-platform path issues."""
    if sys.version_info >= (3, 11) and sys.version_info < (3, 12):
        # The cache provider is already disabled via -p no:cacheprovider
        # but we can also clear any cached data that might have cross-platform paths
        pass