# Pull Request Matrix — CamfrogAutoDJ

**Repository:** github.com/cvsz/autodj  
**Basis:** 142 PRs enumerated via `gh api --paginate repos/cvsz/autodj/pulls -f state=all` (complete, single page).  
**Baseline SHA:** `fb5e99a`

## Dimension matrix

| Dimension | Value |
|-----------|-------|
| Total PRs | 142 |
| Open PRs | 0 |
| Open drafts | 0 |
| Merged PRs | 135 |
| Closed, not merged | 4 |
| Closed drafts | 3 |
| PRs with full diff inspected | 142 |
| PRs with recorded disposition | 142 (100%) |
| PRs requiring action on current main | 0 |

## Disposition by category

| Disposition | PRs | Notes |
|-------------|-----|-------|
| MERGED_VERIFIED | 135 | Implementation present on current main (`fb5e99a`) |
| CLOSED_SUPERSEDED | 3 | #120, #121, #118 — auto-audit/auto-fix workflows superseded by #119/#122/#123 |
| CLOSED_DUPLICATE | 1 | #71 — duplicate NSIS `MUI_ABORTWARNING` fix (#72/#74/#75/#78) |
| DRAFT_INCOMPLETE | 3 | #101, #5, #4 — closed drafts, incomplete, superseded by merged work |

## PRs closed without merge (detail)

| # | Head branch | Closed | Title | Reason | Disposition |
|---|-------------|--------|-------|--------|-------------|
| 121 | feat/auto-fix-workflow-1793999659 | 2026-11-08 | feat: add auto-fix open PRs workflow | Superseded by merged auto-audit/hardening workflows (#119, #122, #123) | CLOSED_SUPERSEDED |
| 120 | feat/auto-audit-1793998118 | 2026-11-08 | feat: add auto audit/review/approve workflow | Superseded by #119 | CLOSED_SUPERSEDED |
| 118 | deploy-auto-audit-workflow | 2026-11-08 | feat: add auto audit/review/approve workflow | Superseded by #119 | CLOSED_SUPERSEDED |
| 71 | fix/installer-nsi-vi-defines-final2 | 2026-11-02 | fix: remove duplicate MUI_ABORTWARNING define from installer.nsi | Duplicate of #72/#74/#75/#78 | CLOSED_DUPLICATE |

## Closed drafts (detail)

| # | Head branch | Title | Disposition |
|---|-------------|-------|-------------|
| 101 | review/sec-001-signing-integrity-2026110 | fix(sec-001): remediate SEC-001 signing integrity and artifact lifecycle | DRAFT_INCOMPLETE |
| 5 | fix/autodj-test-baseline-20261028-run11 | fix(ci): restore deterministic AutoDJ test baseline | DRAFT_INCOMPLETE |
| 4 | fix/codeql-actions-version-alignment-202 | fix(ci): align CodeQL action versions | DRAFT_INCOMPLETE |

## Mergeability

No PR is currently open, so there are no merge conflicts to resolve and no mergeability gate to pass. The current `main` HEAD (`fb5e99a`) already incorporates all merged PR work. Any new PR opened from this audit will be branched from `fb5e99a`.
