"""Tiny pytest stand-in: supports test_*.py functions, monkeypatch, tmp_path, pytest.raises,
pytest.importorskip, pytest.skip, pytest.mark.parametrize (basic). Used by `make test` / tools/mutate.sh
ONLY when the real pytest is not installed (dev extra not installed yet). Prefer `pip install -e .[dev]`
and real pytest for anything beyond a quick check -- this exists so `make test` always works out of the box."""
import importlib, importlib.util, inspect, sys, types, tempfile, traceback, pathlib, os, re

class Skip(Exception): pass

def _skip(msg=""): raise Skip(msg)
def importorskip(name):
    try: return importlib.import_module(name)
    except ImportError: raise Skip(f"no module {name}")

class _Raises:
    def __init__(self, exc, match=None): self.exc, self.match, self.value = exc, match, None
    def __enter__(self): return self
    def __exit__(self, t, v, tb):
        if t is None: raise AssertionError(f"DID NOT RAISE {self.exc}")
        if not issubclass(t, self.exc): return False
        if self.match and not re.search(self.match, str(v)): raise AssertionError(f"{v!r} !~ {self.match!r}")
        self.value = v; return True

class _Mark:
    def parametrize(self, names, values):
        def deco(fn):
            fn._params = (names, values); return fn
        return deco
    def __getattr__(self, n):
        return lambda *a, **k: (lambda fn: fn)

class MonkeyPatch:
    def __init__(self): self._undo = []
    def setattr(self, target, name=None, value=None, raising=True):
        if isinstance(target, str):
            mod, _, attr = target.rpartition("."); value = name; obj = importlib.import_module(mod); name = attr
        else: obj = target
        self._undo.append((obj, name, getattr(obj, name, _MISSING)))
        setattr(obj, name, value)
    def setitem(self, d, k, v): self._undo.append((d, k, d.get(k, _MISSING), 'item')); d[k] = v
    def setenv(self, k, v): self._undo.append((os.environ, k, os.environ.get(k, _MISSING))); os.environ[k] = v
    def undo(self):
        for rec in reversed(self._undo):
            if len(rec) == 4:
                d, k, old, _ = rec; (d.pop(k, None) if old is _MISSING else d.__setitem__(k, old)); continue
            obj, name, old = rec
            if isinstance(obj, os._Environ):
                (obj.pop(name, None) if old is _MISSING else obj.__setitem__(name, old))
            elif old is _MISSING: delattr(obj, name)
            else: setattr(obj, name, old)
_MISSING = object()

pytest = types.ModuleType("pytest")
pytest.skip, pytest.importorskip, pytest.raises, pytest.mark = _skip, importorskip, _Raises, _Mark()
pytest.fixture = lambda *a, **k: (lambda f: f) if not (a and callable(a[0])) else a[0]
sys.modules["pytest"] = pytest

def main(argv):
    arg = argv[0] if argv else "tests"
    want_name = None  # pytest-style file.py::test_name: run only that one function
    if "::" in arg:
        arg, want_name = arg.split("::", 1)
    root = pathlib.Path(arg).resolve()
    files = [root] if root.is_file() else sorted(root.glob("test_*.py"))
    tests_dir = root.parent if root.is_file() else root  # the tests/ dir, whether given a file or the dir itself
    sys.path.insert(0, str(tests_dir)); sys.path.insert(0, str(tests_dir.parent))  # project root, for `import camfrog_autodj`
    ok = fail = skip = 0
    for f in files:
        spec = importlib.util.spec_from_file_location(f.stem, f); m = importlib.util.module_from_spec(spec)
        sys.modules[f.stem] = m
        try: spec.loader.exec_module(m)
        except Exception: print(f"ERROR collecting {f.name}"); traceback.print_exc(); fail += 1; continue
        for name, fn in inspect.getmembers(m, inspect.isfunction):
            if not name.startswith("test_") or fn.__module__ != m.__name__: continue
            if want_name and name != want_name: continue
            cases = [{}]
            if hasattr(fn, "_params"):
                names, vals = fn._params; names = [n.strip() for n in names.split(",")]
                cases = [dict(zip(names, v if len(names) > 1 else (v,))) for v in vals]
            for kw in cases:
                mp = MonkeyPatch(); tmp = pathlib.Path(tempfile.mkdtemp())
                args = {}
                for p in inspect.signature(fn).parameters:
                    args[p] = kw.get(p) if p in kw else mp if p == "monkeypatch" else tmp if p == "tmp_path" else None
                try: fn(**args); ok += 1; print(f"PASS {f.name}::{name}")
                except Skip as s: skip += 1; print(f"SKIP {f.name}::{name} ({s})")
                except Exception: fail += 1; print(f"FAIL {f.name}::{name}"); traceback.print_exc()
                finally: mp.undo()
    print(f"\n{ok} passed, {fail} failed, {skip} skipped"); return 1 if fail else 0

if __name__ == "__main__": sys.exit(main(sys.argv[1:]))
