# AutoDJ Release Tag Signing Procedure

**Repository:** `cvsz/autodj`  
**Project:** ZEAZDEV AutoDJ  
**Date:** 2026-11-02  
**Status:** Policy defined; no tags created during this task  

---

## 1. Purpose

This document defines the policy and procedure for GPG-signing annotated Git tags for AutoDJ releases. Tag signing provides cryptographic assurance that:

- The tag was created by an authorized maintainer
- The tag points to the exact commit that was validated by CI
- The tag has not been tampered with or replaced
- The release version matches the codebase version

## 2. Signing Policy

### 2.1 Tag Type

- **Annotated tags only** (`git tag -a` or `git tag -s`)
- Lightweight tags (`git tag <name>` without `-a` or `-s`) are **not** acceptable for releases
- Tag format: `v<major>.<minor>.<patch>` (e.g., `v0.2.7`, `v1.0.0`)

### 2.2 Signature Type

- **GPG-signed tags** required (`git tag -s` or `git tag -u <keyid>`)
- Unsigned annotated tags are **not** acceptable for releases
- The signer's GPG key must be registered with GitHub and verified

### 2.3 Tag Target

- The tag must point to the exact commit that passed all CI validation gates
- The commit SHA must match the SHA recorded in CI evidence
- The tag must not be moved, force-updated, or replaced after creation
- **Never rewrite or replace existing published tags**

### 2.4 Version Consistency

- The tag name must match the project version in `pyproject.toml`, `camfrog_autodj/__init__.py`, and `version_info.txt`
- Version consistency is verified by `tests/test_version_and_release.py::test_versions_agree`
- Tag name format: `v{version}` (e.g., `v0.2.7` for version `0.2.7`)

## 3. Signing Procedure

### 3.1 Prerequisites

1. GPG key pair generated and configured for Git:
   ```bash
   git config user.signingkey <key-id>
   git config commit.gpgsign true
   git config tag.gpgsign true
   ```
2. GPG public key added to GitHub account (Settings → SSH and GPG keys)
3. Maintainer identity verified on GitHub (COLLABORATOR or higher)

### 3.2 Creating a Signed Tag

```bash
# 1. Verify the exact commit SHA that passed CI
git rev-parse <commit-sha>

# 2. Verify version consistency across all files
python -m pytest tests/test_version_and_release.py::test_versions_agree -v

# 3. Create the annotated, GPG-signed tag
git tag -s v<version> <commit-sha> -m "CamfrogAutoDJ v<version>

Release notes summary."

# 4. Verify the tag signature
git tag -v v<version>

# 5. Verify the tag target SHA matches CI-validated commit
git rev-parse v<version>^{}
```

### 3.3 Verification Checklist

| Check | Command | Expected Result |
|-------|---------|-----------------|
| Tag is annotated | `git cat-file -t v<version>` | `tag` |
| Tag is signed | `git tag -v v<version>` | `gpg: Good signature` |
| Tag target matches CI commit | `git rev-parse v<version>^{}` | Same SHA as CI-validated commit |
| Tag name matches version | Compare `v<version>` with `pyproject.toml` version | Match |
| Signer identity | `git tag -v v<version>` | `gpg: Good signature from <maintainer>` |
| No existing tag replaced | `git tag -l v<version>` | Only one tag with this name exists |

## 4. Verification by Independent Reviewer

The independent reviewer (`policedbc`) must:

1. Fetch the signed tag:
   ```bash
   git fetch origin tag v<version>
   ```

2. Verify the signature:
   ```bash
   git tag -v v<version>
   ```

3. Verify the tag target matches the CI-validated commit SHA from the release workflow evidence

4. Confirm the tag was not force-updated or replaced:
   ```bash
   git log --oneline v<version>..main | head -5
   ```

5. Document verification in the PR review comments

## 5. What NOT to Do

| Prohibited Action | Reason |
|-------------------|--------|
| Create lightweight tags for releases | No signature or message, cannot be verified |
| Use unsigned annotated tags | No cryptographic proof of signer identity |
| Move or force-update an existing tag | Breaks signature verification, confuses consumers |
| Tag a commit that hasn't passed CI | Release may contain unverified changes |
| Tag with a version that doesn't match codebase | Version drift, confusing for consumers |
| Share GPG private keys | Compromise of signing identity |
| Create tags during remediation or pre-release tasks | Tags are release artifacts, not development artifacts |

## 6. What This Task Does NOT Do

Per the task instructions:

- **No tag is created** during this task
- **No release is published** during this task
- **No existing tag is modified or replaced**
- The v0.2.6 tag exists but is **unsigned**; per policy, future releases should use signed tags

## 7. Current Tag State

| Tag | Type | Signed | Target Commit | Date |
|-----|------|--------|---------------|------|
| v0.2.4 | annotated | No | Unknown | Before v0.2.6 |
| v0.2.5 | annotated | No | Unknown | Before v0.2.6 |
| v0.2.6 | annotated | **No** | `e2ec1013859e587b41dcd047a234b0cf14cd7580` | 2026-11-01 |

The v0.2.6 tag is not GPG signed. Future release tags (v0.2.7 and later) should follow this signing procedure.

## 8. Rollback

If a signed tag is created in error:

1. **Do not** force-update or delete the tag if it has been pushed
2. Notify all consumers that the tag should not be trusted
3. Create a new tag with a different version number for the corrected release
4. Document the superseded tag in the release notes
