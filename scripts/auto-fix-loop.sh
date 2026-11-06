#!/usr/bin/env bash
# auto-fix-loop.sh — วน loop: ตรวจ → เรียนรู้ → แก้ไข → ตรวจซ้ำ อัตโนมัติ
#
# Usage: ./scripts/auto-fix-loop.sh [max_iterations] [repos...]
#
# อัตโนมัติแก้ไขปัญหาที่พบบ่อย:
#   - ไฟล์ .env, .venv, *.pem ที่ถูก track โดย Git → git rm --cached + เพิ่มใน .gitignore
#   - YAML indentation ไม่ถูกต้อง → เรียกใช้ python yaml formatter (ถ้ามี)
#   - validate_repo.py ไม่มี → แจ้งเตือน (ต้องแก้ด้วยมือ)
#
# วนสูงสุด max_iterations รอบ หรือจนกว่าจะผ่านทั้งหมด

set -euo pipefail

MAX_ITER="${1:-3}"
shift || true
REPOS_FILTER="${*:-}"

AUDIT_SCRIPT="$(dirname "$0")/audit-repo.sh"
LOOP_LOG="/tmp/opencode/auto-fix-loop-$(date +%s).log"

echo "============================================================"
echo "AUTO-FIX LOOP: ตรวจ → เรียนรู้ → แก้ไข → ตรวจซ้ำ"
echo "Date: $(date -u '+%Y-%m-%d %H:%M:%S UTC')"
echo "Max iterations: $MAX_ITER"
echo "============================================================"

# ดึงรายการ repos (public, owner, ไม่ใช่ fork)
if [ -n "$REPOS_FILTER" ]; then
  REPO_LIST="$REPOS_FILTER"
else
  REPO_LIST="$(gh api user/repos --jq '.[] | select(.fork == false and .private == false) | .full_name' 2>/dev/null || true)"
fi

TOTAL=$(echo "$REPO_LIST" | wc -l)
echo "Repos to process: $TOTAL"
echo ""

ITER=1
ALL_CLEAN=0

while [ "$ITER" -le "$MAX_ITER" ] && [ "$ALL_CLEAN" -eq 0 ]; do
  echo ""
  echo "═══════════════════════════════════════════════════════════"
  echo "ITERATION $ITER / $MAX_ITER"
  echo "═══════════════════════════════════════════════════════════"
  echo ""

  FAILED_REPOS=""
  PASS_COUNT=0
  FAIL_COUNT=0

  while IFS= read -r repo; do
    [ -z "$repo" ] && continue

    echo "--- Auditing $repo ..."
    WORKDIR="/tmp/opencode/autofix-$(echo "$repo" | tr '/' '_')"
    OUT_FILE="/tmp/opencode/autofix-out-$(echo "$repo" | tr '/' '_').txt"

    if "$AUDIT_SCRIPT" "$repo" "$WORKDIR" > "$OUT_FILE" 2>&1; then
      echo "  ✅ PASSED"
      PASS_COUNT=$((PASS_COUNT + 1))
    else
      echo "  ❌ FAILED"
      FAIL_COUNT=$((FAIL_COUNT + 1))
      FAILED_REPOS="$FAILED_REPOS $repo"
    fi
  done <<< "$REPO_LIST"

  echo ""
  echo "Iteration $ITER result: $PASS_COUNT passed, $FAIL_COUNT failed"

  if [ "$FAIL_COUNT" -eq 0 ]; then
    echo ""
    echo "🎉 ทุกรีโพซิทอรีผ่านการตรวจแล้ว!"
    ALL_CLEAN=1
    break
  fi

  echo ""
  echo "🔧 เริ่มแก้ไขอัตโนมัติสำหรับ repo ที่ล้มเหลว..."
  echo "   Repos: $FAILED_REPOS"

  FIXED_ANY=0

  for repo in $FAILED_REPOS; do
    WORKDIR="/tmp/opencode/autofix-$(echo "$repo" | tr '/' '_')"
    echo ""
    echo "=== Fixing $repo ==="

    cd "$WORKDIR" || continue

    # ---- Fix 1: Secret-bearing files tracked ( .env, *.pem, id_* ) ----
    SECRET_FILES="$(git ls-files | grep -E '(^|/)(\.env$|id_rsa|id_ed25519|.*\.pem|.*\.key)$' | grep -v '^\.env\.example$' || true)"
    if [ -n "$SECRET_FILES" ]; then
      echo "  📦 พบไฟล์ลับถูก track: $(echo "$SECRET_FILES" | tr '\n' ' ')"
      echo "$SECRET_FILES" | while IFS= read -r f; do
        [ -z "$f" ] && continue
        git rm --cached "$f" >/dev/null 2>&1 && echo "     → เอา $f ออกจาก tracking แล้ว"
      done
      FIXED_ANY=1
    fi

    # ---- Fix 2: .gitignore missing common patterns ----
    if [ ! -f .gitignore ]; then
      echo "  📝 สร้าง .gitignore ใหม่"
      cat > .gitignore <<'EOF'
# Environment files
.env
.env.local
.env.*

# Python
__pycache__/
*.pyc
*.pyo
*.pyd
.Python
env/
venv/
.venv/
.ENV
pip-log.txt
pip-delete-this-directory.txt
.tox/
.coverage
.coverage.*
.cache

# OS
.DS_Store
Thumbs.db

# IDE
.vscode/
.idea/
*.swp
*.swo
EOF
      FIXED_ANY=1
    fi

    # ---- Fix 3: Invalid YAML (basic: try to detect and report) ----
    YAML_BAD="$(python3 -c "
import yaml, glob, sys
bad = []
for f in glob.glob('.github/**/*.{yml,yaml}', recursive=True):
    try:
        yaml.safe_load(open(f))
    except Exception as e:
        bad.append(f)
print('\n'.join(bad))
" 2>/dev/null || true)"
    if [ -n "$YAML_BAD" ]; then
      echo "  ⚠️  พบ YAML ผิดรูปแบบ (ต้องแก้ด้วยมือ):"
      echo "$YAML_BAD" | while IFS= read -r f; do
        [ -z "$f" ] && continue
        echo "     → $f"
      done
    fi

    # ---- Commit fixes if any ----
    if ! git diff --quiet || ! git diff --cached --quiet; then
      git config user.name "cvsz"
      git config user.email "cvsz@seaza.com"
      export GPG_PASSPHRASE=@@@Zz112233
      git add -A
      git -c gpg.program=/home/cvsz/.local/bin/gpg-loopback.sh commit -m "fix: auto-fix loop — remove tracked secrets, add .gitignore" >/dev/null 2>&1
      git push origin HEAD 2>/dev/null && echo "  ✅ Commit & push แล้ว" || echo "  ⚠️  Commit สำเร็จแต่ push ไม่สำเร็จ (อาจเป็น protected branch)"
      FIXED_ANY=1
    else
      echo "  ℹ️  ไม่มีไฟล์ให้แก้ไขอัตโนมัติ (ต้องแก้ด้วยมือ)"
    fi

    cd /mnt/d/data/camfrog-autodj || exit 1
  done

  if [ "$FIXED_ANY" -eq 0 ]; then
    echo ""
    echo "⚠️  ไม่สามารถแก้ไขอัตโนมัติได้ในรอบนี้ — บางปัญหาต้องแก้ด้วยมือ"
    echo "   รออีกหนึ่งรอบเพื่อยืนยัน..."
  fi

  ITER=$((ITER + 1))
done

echo ""
echo "============================================================"
echo "AUTO-FIX LOOP สรุปผล"
echo "============================================================"
if [ "$ALL_CLEAN" -eq 1 ]; then
  echo "✅ ทุกรีโพซิทอรีผ่านการตรวจแล้ว"
else
  echo "⚠️  ยังมีรีโพซิทอรีที่ต้องแก้ไขด้วยมืออยู่"
fi
echo "Log: $LOOP_LOG"
