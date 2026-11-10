"""Tiny pytest stand-in: supports test_*.py functions, monkeypatch, tmp_path, pytest.raises,
pytest.importorskip, pytest.skip, pytest.mark.parametrize (basic). Used by `make test` / tools/mutate.sh
ONLY when the real pytest is not installed (dev extra not installed yet). Prefer `pip install -e .[dev]`
and real pytest for anything beyond a quick check -- this exists so `make test` always works out of the box."""

import importlib
import importlib.util
import inspect
import os
import pathlib
import re
import sys
import tempfile
import traceback
import types


class SkipError(Exception):
    pass


def _skip(msg=""):
    raise SkipError(msg)


def importorskip(name):
    try:
        return importlib.import_module(name)
    except ImportError as err:
        raise SkipError(f"no module {name}") from err


class _Raises:
    def __init__(self, exc, match=None):
        self.exc, self.match, self.value = exc, match, None

    def __enter__(self):
        return self

    def __exit__(self, t, v, tb):
        if t is None:
            raise AssertionError(f"DID NOT RAISE {self.exc}")
        if not issubclass(t, self.exc):
            return False
        if self.match and not re.search(self.match, str(v)):
            raise AssertionError(f"{v!r} !~ {self.match!r}")
        self.value = v
        return True


class _Mark:
    def parametrize(self, names, values):
        def deco(fn):
            fn._params = (names, values)
            return fn

        return deco

    def __getattr__(self, n):
        return lambda *a, **k: lambda fn: fn


class MonkeyPatch:
    def __init__(self):
        self._undo = []

    def setattr(self, target, name=None, value=None, raising=True):
        if isinstance(target, str):
            mod, _, attr = target.rpartition(".")
            value = name
            obj = importlib.import_module(mod)
            name = attr
        else:
            obj = target
        self._undo.append((obj, name, getattr(obj, name, _MISSING)))
        setattr(obj, name, value)

    def setitem(self, d, k, v):
        self._undo.append((d, k, d.get(k, _MISSING), "item"))
        d[k] = v

    def setenv(self, k, v):
        self._undo.append((os.environ, k, os.environ.get(k, _MISSING)))
        os.environ[k] = v

    def undo(self):
        for rec in reversed(self._undo):
            if len(rec) == 4:
                d, k, old, _ = rec
                (d.pop(k, None) if old is _MISSING else d.__setitem__(k, old))
                continue
            obj, name, old = rec
            if isinstance(obj, os._Environ):
                (obj.pop(name, None) if old is _MISSING else obj.__setitem__(name, old))
            elif old is _MISSING:
                delattr(obj, name)
            else:
                setattr(obj, name, old)


_MISSING = object()

# Create a typed pytest module stub
pytest = types.ModuleType("pytest")
pytest.skip = _skip  # type: ignore[attr-defined]
pytest.importorskip = importorskip  # type: ignore[attr-defined]
pytest.raises = _Raises  # type: ignore[attr-defined]
pytest.mark = _Mark()  # type: ignore[attr-defined]
pytest.fixture = lambda *a, **k: (lambda f: f) if not (a and callable(a[0])) else a[0]  # type: ignore[attr-defined]
sys.modules["pytest"] = pytest


def main(argv):
    arg = argv[0] if argv else "tests"
    want_name = None  # pytest-style file.py::test_name: run only that one function
    if "::" in arg:
        arg, want_name = arg.split("::", 1)
    root = pathlib.Path(arg).resolve()
    files = [root] if root.is_file() else sorted(root.glob("test_*.py"))
    tests_dir = root.parent if root.is_file() else root
    sys.path.insert(0, str(tests_dir))
    sys.path.insert(0, str(tests_dir.parent))  # project root, for `import camfrog_autodj`
    ok = fail = skip = 0
    for f in files:
        m = _load_module(f)
        if m is None:
            fail += 1
            continue
        o, fl, sk = _run_tests_in_module(m, f, want_name)
        ok += o
        fail += fl
        skip += sk
    print(f"\n{ok} passed, {fail} failed, {skip} skipped")
    return 1 if fail else 0


def _load_module(f):
    """Import one test file as a module; return None on collection error."""
    spec = importlib.util.spec_from_file_location(f.stem, f)
    if spec is None:
        return None
    m = importlib.util.module_from_spec(spec)
    sys.modules[f.stem] = m
    if spec.loader is None:
        return None
    try:
        spec.loader.exec_module(m)
    except (ImportError, SyntaxError, TypeError, AttributeError, OSError):
        print(f"ERROR collecting {f.name}")
        traceback.print_exc()
        return None
    return m


def _run_tests_in_module(m, f, want_name):
    """Run every test_* function in module *m*; return (ok, fail, skip)."""
    ok = fail = skip = 0
    for name, fn in inspect.getmembers(m, inspect.isfunction):
        if not name.startswith("test_") or fn.__module__ != m.__name__:
            continue
        if want_name and name != want_name:
            continue
        for kw in _param_cases(fn):
            ok_delta, fl_delta, sk_delta = _run_case(fn, m, kw, f.name, name)
            ok += ok_delta
            fail += fl_delta
            skip += sk_delta
    return ok, fail, skip


def _param_cases(fn):
    """The parameterised cases for *fn*: a list of kwarg dicts (default [{}])."""
    cases: list[dict[str, object]] = [{}]
    if hasattr(fn, "_params"):
        names, vals = fn._params
        names = [n.strip() for n in names.split(",")]
        cases = [dict(zip(names, v if len(names) > 1 else (v,), strict=False)) for v in vals]
    return cases


def _run_case(fn, m, kw, file_name, func_name):
    """Run one parameterised test case; return (ok, fail, skip) deltas."""
    mp = MonkeyPatch()
    tmp = pathlib.Path(tempfile.mkdtemp())
    args = {}
    for p in inspect.signature(fn).parameters:
        args[p] = (
            kw.get(p) if p in kw else mp if p == "monkeypatch" else tmp if p == "tmp_path" else None
        )
    try:
        fn(**args)
        print(f"PASS {file_name}::{func_name}")
        return 1, 0, 0
    except SkipError as s:
        print(f"SKIP {file_name}::{func_name} ({s})")
        return 0, 0, 1
    except (
        AssertionError,
        TypeError,
        ValueError,
        KeyError,
        IndexError,
        RuntimeError,
        OSError,
        ImportError,
    ):
        print(f"FAIL {file_name}::{func_name}")
        traceback.print_exc()
        return 0, 1, 0
    finally:
        mp.undo()


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
