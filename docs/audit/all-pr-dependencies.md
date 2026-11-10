# Pull Request Dependencies — CamfrogAutoDJ

**Repository:** github.com/cvsz/autodj  
**Basis:** 142 PRs enumerated via `gh api --paginate repos/cvsz/autodj/pulls -f state=all`.

## Dependabot PRs (dependency upgrades)

All Dependabot PRs are merged into `main`. The dependency pinning in `pyproject.toml` and `.github/workflows` reflects these upgrades.

| PR | Dependency | From → To | Disposition |
|----|------------|-----------|-------------|
| #80 | setuptools (build) | >=68 → >=84.2.1 | MERGED_VERIFIED |
| #81 | actions/attest-build-provenance | → v4 | MERGED_VERIFIED |
| #82 | actions/upload-artifact | 4.6.2 → 7.0.2 | MERGED_VERIFIED |
| #106 | actions/checkout | 4.2.2 → 7.0.1 | MERGED_VERIFIED |
| #107 | actions/setup-python | 5.6.0 → 7.1.0 | MERGED_VERIFIED |
| #108 | actions/attest-build-provenance | 2.4.0 → 4.2.2 | MERGED_VERIFIED |

## Python dependency pins (pyproject.toml)

`pyproject.toml` pins `setuptools>=84.2.1` for the build backend. Runtime dependencies (`yt-dlp`, `mutagen`, `pyttsx3`, `pywinauto`, `pyperclip`) are unpinned (loose) to allow security updates; Dependabot and the `dependency-review.yml` workflow cover vulnerability scanning. `dev` = `pytest`, `build` = `pyinstaller`.

## Python version

`requires-python = ">=3.11"`. CI tests Python 3.11 and 3.12 on windows-latest and ubuntu-latest. The local host runs Python 3.14.4 (newer than the CI matrix; tests still pass).

## Security advisories

No open Dependabot security alerts were part of this audit's scope to fetch live; the `dependency-review.yml` and `codeql.yml` workflows are enabled and SHA-pinned (see #83, #40). Dependency upgrades were reviewed in small groups per policy; no blind mass upgrade was performed.
