# Auto Audit + Review + Approve via policedbc (GitHub Actions)

Automated PR auditing, review, and approval performed by the `policedbc`
service account through GitHub Actions.

## Architecture

```
Pull Request opened
        │
        ▼
┌─────────────────┐
│  Audit checks   │  validate_repo.py, secret scan, YAML validation
│  (policedbc)    │
└─────────────────┘
        │
        ▼
┌─────────────────┐
│ Safety gate     │  Skip auto-approve if security-sensitive
│                 │  paths changed (per CODEOWNERS)
└─────────────────┘
        │
   ┌────┴────┐
   │         ▼
   ▼    ┌─────────────┐
Pass   │ Review +    │  policedbc leaves review comment
   │    Approve      │  Auto-approves if safe
   ▼    └─────────────┘
Fail   │ Comment only│  Lists failures, no approval
   ▼
```

## Prerequisites

### 1. policedbc GitHub account must be a collaborator

Invite `policedbc` to the `cvsz/autodj` repository with **Write** permission
(needed to create reviews and approve PRs).

### 2. Create a Personal Access Token (PAT) for policedbc

Log in as `policedbc` on GitHub, then:

**Settings → Developer settings → Personal access tokens → Fine-grained tokens**

- Repository access: `cvsz/autodj` (read & write)
- Permissions:
  - Pull requests: **Read & write**
  - Issues: **Read & write**
  - Contents: **Read**
  - Metadata: **Read**

Copy the token (starts with `github_pat_...` or `ghp_...`).

### 3. Add the PAT as a repository secret

In `cvsz/autodj`:

**Settings → Secrets and variables → Actions → New repository secret**

| Name | Value |
|---|---|
| `POLIEDBC_PAT` | `<policedbc PAT>` |

### 4. Configure branch protection (GitHub UI)

**Settings → Branches → Add branch protection rule** for `main`:

| Setting | Value |
|---|---|
| Require a pull request before merging | ✅ |
| Required approving reviews | `1` |
| Dismiss stale approvals when new commits are pushed | ✅ |
| Require review from Code Owners | ✅ |
| Require status checks to pass before merging | ✅ |
| Status checks | `CI`, `tests`, `CodeQL`, `Automated Audit + Review + Approve (policedbc)` |
| Do not bypass the above settings (administrators) | ❌ (keep false) |
| Restrict pushes / require linear history | optional |

## How it works

| Event | Action |
|---|---|
| PR opened/reopened/synchronized | Workflow runs audit checks |
| Audit passes + no security paths changed | policedbc reviews **and approves** |
| Audit passes + security paths changed | policedbc reviews, **requests changes** (human must review) |
| Audit fails | policedbc comments with failures, no approval |
| POLIEDBC_PAT not set | Audit runs, no review/approve (graceful degradation) |

## Security-sensitive paths (auto-approve blocked)

Per `.github/CODEOWNERS`, these paths always require human review:

```
/.github/                 (workflows, CODEOWNERS, etc.)
SECURITY.md
AGENTS.md
installer.nsi / install.ps1 / install-full-auto.ps1 / build.ps1
config.toml / config.example.toml
```

If a PR touches any of these, policedbc will **not** auto-approve even if audit passes.

## Self-hosted runner (optional)

If you prefer a self-hosted runner instead of GitHub-hosted `ubuntu-latest`:

1. **Settings → Actions → Runners → New self-hosted runner** → Linux
2. Follow the setup commands to download, configure, and start the runner
3. Change `runs-on: ubuntu-latest` to `runs-on: self-hosted` in the workflow
4. Add label `self-hosted` to the runner and use `runs-on: [self-hosted, linux]`

## Security warnings

⚠️ **Automated approval is a security risk.** The policedbc account can approve any PR that passes the audit checks. Mitigations:

1. Security-sensitive paths are excluded from auto-approve (CODEOWNERS).
2. `Require review from Code Owners` is enabled in branch protection.
3. `Dismiss stale approvals when new commits are pushed` is enabled.
4. Only grant policedbc the minimum PAT scopes needed.
5. Rotate the POLIEDBC_PAT regularly (every 90 days).

## Testing

1. Create a PR that only touches non-security files (e.g., README)
2. Verify policedbc comments and approves automatically
3. Create a PR that touches `.github/workflows/*.yml`
4. Verify policedbc comments but does **not** approve (human review required)
5. Introduce a validation error, verify audit fails and no approval is given

## Files

| File | Purpose |
|---|---|
| `.github/workflows/automated-audit-review-approve.yml` | Main automation workflow |
| `.github/CODEOWNERS` | Defines security-sensitive paths requiring policedbc |
| `scripts/validate_repo.py` | Repository structure validation |
| `docs/ai/playbooks/auto-audit-review-approve-policedbc.md` | This setup guide |
