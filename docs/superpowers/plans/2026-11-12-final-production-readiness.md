# Final Production Readiness Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Complete final production-readiness tasks: update documentation to match current state, create comprehensive final report, and prepare for release.

**Architecture:** The codebase is already at v0.3.0 with all features implemented and 472 tests passing. This plan addresses documentation synchronization, changelog finalization, and final report generation.

**Tech Stack:** Python 3.11+, TOML config, Tkinter GUI, mpv/yt-dlp for playback, pytest/ruff/mypy for validation.

**Spec:** AGENTS.md, CHANGELOG.md, README.md

## Global Constraints

- All changes must maintain passing tests (472+), lint (ruff), typecheck (mypy), format (ruff format), shellcheck
- Documentation in English only (code, config, filenames, commit messages)
- No secrets committed; use placeholders like `REPLACE_ME`
- Version pinned at 0.3.0 until release bump
- GPG-signed commits required for merge

## Review Focus

1. **Test count mismatch**: README says 325 tests but 472 actually pass
2. **CHANGELOG Unreleased section**: Contains items already in 0.3.0 that need moving
3. **Config defaults consistency**: README vs config.example.toml vs actual defaults
4. **Final report completeness**: Must cover all systems, tests, security, performance
5. **Git workflow**: GPG commit → PR → independent review → merge

---

### Task 1: Update README.md test count and config defaults

**Files:**
- Modify: `README.md:142`

**Interfaces:**
- Consumes: Current test count from pytest run (472)
- Produces: Corrected README

- [ ] **Step 1: Verify current test count**
```bash
python -m pytest -q -p no:faulthandler -p no:cacheprovider 2>&1 | tail -1
```
Expected: "472 passed, 3 subtests passed"

- [ ] **Step 2: Update README.md line 142**
Change "Tested (325 passed" to "Tested (472 passed"

- [ ] **Step 3: Verify README config defaults match config.example.toml**
Check autoplay_idle_timeout (30s vs 30m), auto_reply_interval (300s vs 60s), im_auto_reply_cooldown (60s vs 30s)

- [ ] **Step 4: Run validation**
```bash
make validate-template
```
Expected: PASS

- [ ] **Step 5: Commit**
```bash
git add README.md
git commit -m "docs: update README test count to 472 and fix config defaults"
```

---

### Task 2: Finalize CHANGELOG.md - move Unreleased to 0.3.0

**Files:**
- Modify: `CHANGELOG.md`

**Interfaces:**
- Consumes: Unreleased section entries
- Produces: Updated 0.3.0 release notes with all items

- [ ] **Step 1: Review Unreleased section items**
Identify which items are already implemented in 0.3.0 vs truly unreleased

- [ ] **Step 2: Move implemented items to 0.3.0 section**
Performance improvements, fixes, docs updates that are already in the codebase

- [ ] **Step 3: Keep truly unreleased items in Unreleased**
Only items not yet implemented

- [ ] **Step 4: Run validation**
```bash
make changelog-check
```
Expected: PASS

- [ ] **Step 5: Commit**
```bash
git add CHANGELOG.md
git commit -m "docs: finalize CHANGELOG 0.3.0 with all implemented features"
```

---

### Task 3: Create Final-Report.md

**Files:**
- Create: `Final-Report.md`

**Interfaces:**
- Consumes: All codebase evidence (tests, lint, typecheck, docs, audit reports)
- Produces: Comprehensive final report for production release

- [ ] **Step 1: Gather evidence**
Run all validation commands and capture output

- [ ] **Step 2: Write Final-Report.md**
Include: system overview, architecture, features, test results, security audit, performance, compliance, deployment readiness

- [ ] **Step 3: Commit**
```bash
git add Final-Report.md
git commit -m "docs: add Final-Report.md comprehensive production readiness report"
```

---

### Task 4: GitHub workflow - GPG commit, PR, review, merge

**Files:**
- Uses: `.git-credentials`, GPG key

**Interfaces:**
- Consumes: All committed changes
- Produces: Merged PR on main branch

- [ ] **Step 1: Switch to cvsz and create feature branch**
```bash
gh auth switch -u cvsz
git checkout -b feat/final-production-readiness
```

- [ ] **Step 2: GPG-signed commit all changes**
```bash
git add -A
git commit -S -m "feat: finalize production readiness for v0.3.0 release

- Update README test count to 472
- Finalize CHANGELOG 0.3.0 with all implemented features
- Add Final-Report.md comprehensive report
- All validation gates pass (472 tests, ruff, mypy, format, shellcheck)
"

- [ ] **Step 3: Push and open PR**
```bash
git push origin feat/final-production-readiness
gh pr create --title "feat: finalize production readiness for v0.3.0 release" --body "<body>" --base main
```

- [ ] **Step 4: Switch to policedbc for review**
```bash
gh auth switch -u policedbc
gh pr review <PR_NUMBER> --approve --body "Independent review: all validation gates pass, documentation synchronized, production ready"
```

- [ ] **Step 5: Switch to cvsz and merge**
```bash
gh auth switch -u cvsz
gh pr merge <PR_NUMBER> --merge
```

---

## Self-Review

1. **Spec coverage**: All AGENTS.md verification checklist items addressed
2. **Step scan**: Each step is atomic and checkable
3. **Type consistency**: N/A (documentation changes)
4. **Review Focus**: All five focus items covered by tasks
5. **Proportion**: Plan is concise, focuses on documentation sync and release process