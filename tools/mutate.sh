#!/bin/bash
# Re-run the mutation checks behind tests/test_hardening.py (see AUDIT.md): break one fix at a time in a
# scratch copy of the project and confirm the matching regression test fails. Proves the tests actually
# catch the bugs they claim to, not just that they pass on unmodified code.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SCRATCH="$(mktemp -d)"
trap 'rm -rf "$SCRATCH"' EXIT

run_one() {  # file, old, new
  rm -rf "$SCRATCH/p" && cp -r "$ROOT" "$SCRATCH/p"
  cd "$SCRATCH/p"
  python3 - "$1" "$2" "$3" <<'PY'
import sys
p, old, new = sys.argv[1:4]
s = open(p, encoding="utf-8").read()
assert s.count(old) == 1, f"mutation target not found/unique in {p}: {old!r} ({s.count(old)})"
open(p, "w", encoding="utf-8").write(s.replace(old, new))
PY
  set +e  # the mutated copy is EXPECTED to fail one test; a nonzero exit here is success, not a script error
  if command -v pytest >/dev/null 2>&1 && python3 -c "import pytest" 2>/dev/null; then
    PYTHONPATH=. python3 -m pytest -q tests/ 2>&1 | grep -E "^FAILED|passed|failed" | sed 's/^/   /'
  else
    PYTHONPATH=. python3 tools/minipytest.py tests/ 2>&1 | grep -E "^FAIL |passed" | sed 's/^/   /'
  fi
  set -e
  cd "$ROOT"
}

echo "M1: disable echo guard in chat loop"
run_one camfrog_autodj/engine.py "or self._is_echo(msg.text)" "or False"
echo "M2: disable failure back-off/throttle (always announce)"
run_one camfrog_autodj/engine.py "if fails <= MAX_FAIL_ANNOUNCE:" "if True:"
echo "M3: remove post-lookup limit re-check"
run_one camfrog_autodj/commands.py '            if e.queue.count_by(m.user) >= c.max_requests_per_user:
                raise UserError(e.t("max_requests", n=c.max_requests_per_user))
            src = tracks[0].source' '            src = tracks[0].source'
echo "M4: remove duplicate-request guard"
run_one camfrog_autodj/commands.py 'raise UserError(e.t("already_queued"))' 'pass'
echo "M5: remove-by-position instead of identity"
run_one camfrog_autodj/commands.py "if e.queue.remove_track(t):" "if e.queue.remove(int(a)):"
echo "M6: help line starts with prefix again"
run_one camfrog_autodj/messages.py '"help_base": "Commands: {p}play' '"help_base": "{p}play'
echo "M7: config accepts string admins"
run_one camfrog_autodj/config.py "        if not ok:
            hint" "        if False:
            hint"
echo
echo "All mutations applied; each should show exactly one FAIL above (its own regression test)."
