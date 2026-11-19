# CAMFROG AUTODJ — MASTER REPOSITORY ORGANIZATION & CLEANUP PROMPT

## SYSTEM ROLE

Act as a Principal Software Architect, Senior Python Engineer, DevSecOps Engineer, Windows Application Specialist, and Independent Code Auditor.

Your mission is to transform the existing Camfrog AutoDJ repository into a clean, maintainable, secure, high-performance, enterprise-quality production codebase.

**Repository:** `/mnt/d/data/camfrog-autodj/`

**Primary objective:** Establish a Single Source of Truth (SSOT), eliminate structural disorder, consolidate duplicate implementations, and preserve all existing working functionality.

---

## 1. MANDATORY FIRST STEPS

Before modifying anything:

1. Read `zeaz.md` if available in the repository or its applicable parent directories.
2. Read `AGENTS.md`, `CLAUDE.md`, `OPENCODE.md`, and all applicable agent instructions.
3. Inspect `.git/`, current branch, working tree, and recent commit history.
4. Read `README.md`, `pyproject.toml`, `CHANGELOG.md`, `SECURITY.md`, and existing implementation plans.
5. Inspect the complete repository tree.
6. Identify entry points, dependencies, modules, plugins, configuration, scripts, tests, installers, and build artifacts.
7. Establish a baseline of existing tests and application behavior.
8. Identify secrets, credentials, certificates, and sensitive files.

Do not overwrite uncommitted user changes.

## 2. TARGET DIRECTORY ARCHITECTURE

Analyze and migrate toward this logical structure. Adapt it to actual application dependencies rather than blindly moving files.

```text
camfrog-autodj/
├── .agents/
├── .config/
├── .github/
│   ├── workflows/
│   ├── ISSUE_TEMPLATE/
│   └── PULL_REQUEST_TEMPLATE/
├── .superpowers/
├── artifacts/
├── autodj/
│   ├── core/
│   ├── audio/
│   ├── playback/
│   ├── playlist/
│   ├── plugins/
│   ├── configuration/
│   ├── integrations/
│   ├── security/
│   ├── monitoring/
│   └── cli/
├── components.d/
├── config/
├── docs/
│   ├── architecture/
│   ├── development/
│   ├── deployment/
│   ├── installation/
│   ├── operations/
│   ├── security/
│   └── troubleshooting/
├── evidence/
├── installers/
├── mpv/
├── music/
├── playlist/
├── plugins.d/
├── runtime/
├── scripts/
│   ├── build/
│   ├── install/
│   ├── maintenance/
│   └── validation/
├── templates/
├── tests/
│   ├── unit/
│   ├── integration/
│   ├── e2e/
│   ├── security/
│   └── fixtures/
├── tools/
├── .dockerignore
├── .editorconfig
├── .gitignore
├── AGENTS.md
├── CHANGELOG.md
├── LICENSE
├── Makefile
├── README.md
├── SECURITY.md
└── pyproject.toml
```

The structure above is a target architecture, not an instruction to create empty directories or move every existing folder.

## 3. REPOSITORY CLEANUP

Perform a complete inventory and classify every file.

Categories:

- Production source code
- Configuration
- Tests and fixtures
- Documentation
- Build and installation scripts
- Runtime data
- User data
- Generated artifacts
- Temporary files
- Backups
- Deprecated implementations
- Sensitive files

Specific files and directories requiring investigation:

- `config.toml`
- `config.toml.bak`
- `config_bad_mpv.toml`
- `playlist.json`
- `playlist.json.bak`
- `runtime2-config/`
- `runtime8-invalid-config/`
- `runtime10-invalid-playlist/`
- `test-install4/`
- `test-install-manual/`
- `dist/`
- `artifacts/`
- `logs/`
- `cert/`
- `.env`
- `.git-credentials`
- `Camfrog-AutoDJ-Setup-0.3.0.exe`
- `test_silent.exe`

Rules:

- Never delete user music, playlists, certificates, configuration, or runtime data without explicit authorization.
- Never commit `.env`, credentials, private keys, or access tokens.
- Remove tracked secrets from Git history only through an explicitly reviewed remediation plan.
- Never treat a backup as disposable without comparing its content.
- Move obsolete files into an appropriate archive only when their purpose is understood.
- Remove duplicate code only after confirming functional equivalence.
- Preserve Git history wherever practical.

## 4. ARCHITECTURE REFACTORING

Audit the entire Python codebase.

Requirements:

- Apply SOLID and Clean Architecture where appropriate.
- Separate business logic from infrastructure.
- Eliminate circular dependencies.
- Centralize configuration management.
- Establish consistent exception handling.
- Implement structured logging.
- Validate configuration and playlists before playback.
- Use explicit interfaces for playback engines and plugins.
- Avoid unnecessary abstractions and dependencies.
- Maintain backward compatibility for existing CLI and launcher interfaces.
- Preserve MPV integration and Windows compatibility.

Do not introduce architectural complexity without measurable benefits.

## 5. CONFIGURATION MANAGEMENT

Establish one authoritative configuration strategy.

- Define a canonical configuration schema.
- Use `config.example.toml` as a safe template.
- Validate all configuration values.
- Provide migration support for existing configuration versions.
- Detect invalid MPV executable paths.
- Validate playlist files and media references.
- Prevent secrets from entering logs.
- Preserve existing user configuration during upgrades.

## 6. SECURITY HARDENING

Perform a complete security audit.

Check:

- Hardcoded credentials.
- `.env` exposure.
- `.git-credentials` exposure.
- Certificate and private key handling.
- Unsafe subprocess execution.
- Path traversal.
- Untrusted playlist paths.
- Unsafe file permissions.
- Dependency vulnerabilities.
- Installer privilege escalation.
- Windows 11 security compatibility.
- Docker image and build-context exposure.

Implement secure defaults and document all security-sensitive operations.

## 7. BUILD AND INSTALLATION

Consolidate the Windows build and installer workflow.

Audit:

- `build.ps1`
- `build_exe.bat`
- `build_installer.bat`
- `install.bat`
- `install.ps1`
- `install-full-auto.ps1`
- `installer.nsi`
- `AutoDJ.spec`
- `create_shortcuts.ps1`
- `launch_autodj.bat`
- `launch_autodj.py`

Objectives:

- One canonical build pipeline.
- One canonical installation pipeline.
- Reproducible builds.
- Dependency validation.
- MPV installation detection.
- Windows 11 compatibility.
- Correct shortcuts and application paths.
- Safe upgrade and uninstall behavior.
- Clear installation diagnostics.
- Proper rollback on failed upgrades.

Preserve existing supported installation methods until their replacements are verified.

## 8. TESTING AND QUALITY GATES

Establish reliable automated validation.

Run and improve:

- Unit tests.
- Integration tests.
- Configuration validation tests.
- Playlist validation tests.
- MPV integration tests.
- Installer validation.
- Windows compatibility tests.
- Security tests.
- Regression tests.

Quality requirements:

- No unexplained test regressions.
- No broken imports.
- No duplicate entry points.
- No missing runtime dependencies.
- No secrets in Git.
- No broken installation scripts.
- No undocumented configuration changes.

Do not claim Windows validation passed unless executed on an actual supported Windows environment.

## 9. DOCUMENTATION CONSOLIDATION

Review and consolidate:

- README.md
- ABOUT.md
- ZEAZ-INTRODUCTION.md
- PLAN.md
- ROADMAP.md
- TODO.md
- IMPLEMENTATION_PLAN.md
- IMPLEMENTATION_PLAN_V2.md
- ENTERPRISE_IMPLEMENTATION_PLAN.md
- PERFORMANCE_OPTIMIZATION_PLAN.md
- PERFORMANCE_OPTIMIZATION_SUMMARY.md
- AUDIT_FINDINGS.md
- AUDIT_SUMMARY.md
- Final-Report.md
- VERIFICATION_REPORT.md
- validated.md

Create a consistent documentation hierarchy.

Requirements:

- README as the authoritative project overview.
- Architecture documentation.
- Installation and upgrade instructions.
- Configuration reference.
- Developer guide.
- Security documentation.
- Troubleshooting guide.
- Release and changelog policy.

Preserve historical reports as historical evidence. Do not rewrite historical results to imply that unverified work was completed.

## 10. GIT AND CI/CD

Audit `.github/workflows/`.

Implement appropriate CI gates:

1. Static analysis.
2. Formatting.
3. Type checking.
4. Unit tests.
5. Integration tests.
6. Dependency security checks.
7. Secret scanning.
8. Build verification.
9. Release artifact validation.

Ensure CI does not require paid services or unnecessary external infrastructure.

Use pinned, maintained dependencies and secure GitHub Actions permissions.

## 11. EXECUTION PHASES

Execute autonomously in the following sequence:

**Phase 0 — Discovery**
- Inventory repository.
- Read all applicable instructions.
- Establish Git and test baselines.
- Produce a risk register.

**Phase 1 — Security**
- Identify exposed credentials.
- Protect sensitive data.
- Correct `.gitignore` and Docker build context.
- Preserve user data.

**Phase 2 — Architecture**
- Map dependencies.
- Identify duplicate modules.
- Define canonical architecture.
- Prepare migration plan.

**Phase 3 — Organization**
- Consolidate files and directories.
- Remove verified duplicates.
- Archive obsolete documentation.
- Update import paths and references.

**Phase 4 — Refactoring**
- Improve code quality.
- Centralize configuration.
- Consolidate entry points.
- Preserve backward compatibility.

**Phase 5 — Build and Installer**
- Consolidate build scripts.
- Validate PyInstaller and NSIS.
- Verify installation and upgrade paths.

**Phase 6 — Testing**
- Run complete test suite.
- Fix regressions.
- Validate application startup and MPV integration.

**Phase 7 — Documentation**
- Update README.
- Update architecture documentation.
- Generate migration and maintenance documentation.

**Phase 8 — Final Audit**
- Inspect complete Git diff.
- Check secrets and accidental deletions.
- Run all available quality gates.
- Generate final verification report.

---

## 12. STRICT EXECUTION RULES

- Do actual implementation, not just recommendations.
- Do not stop after producing an audit report.
- Do not create placeholder implementations.
- Do not silently skip failed tests.
- Do not disable tests to obtain green CI.
- Do not change public APIs without compatibility analysis.
- Do not overwrite user data.
- Do not create unnecessary files or abstractions.
- Do not introduce paid dependencies.
- Do not claim success without evidence.
- Use atomic, reviewable changes.
- Maintain a clear execution log.
- Verify every significant migration.
- Preserve the existing application functionality.

If an operation is destructive or its safety cannot be established, stop that operation and report the exact risk while continuing independent safe tasks.

## 13. FINAL DELIVERABLES

Produce:

1. `REPOSITORY_AUDIT.md`
2. `ARCHITECTURE.md`
3. `MIGRATION_REPORT.md`
4. `SECURITY_AUDIT.md`
5. `TEST_REPORT.md`
6. `FINAL_REPORT.md`
7. Updated `README.md`
8. Updated `CHANGELOG.md`
9. Updated `AGENTS.md`

The final report must include:

- Original versus final directory structure.
- Files moved, merged, archived, and removed.
- Duplicate implementations eliminated.
- Security issues found and resolved.
- Architecture improvements.
- Build and installer status.
- Test results with actual counts.
- Remaining issues and limitations.
- Git working-tree status.
- Recommended next actions.

## DEFINITION OF DONE

The project is complete only when:

- There is a clear Single Source of Truth.
- The repository has a consistent structure.
- Duplicate implementations are resolved.
- Sensitive data is protected.
- Existing functionality is preserved.
- Configuration is validated.
- Build and installer workflows are reproducible.
- Tests pass or remaining failures are explicitly documented.
- Documentation reflects the actual implementation.
- No unverified production-readiness claims remain.

**START NOW: Phase 0-9 — inspect the real repository, read all applicable instructions, establish the baseline, and execute the complete phased implementation.**

ข้อควรระวังสำคัญจากโครงสร้างปัจจุบัน
1. .env และ .git-credentials ต้องตรวจสอบก่อน Git operations ทุกครั้ง
2. cert/ ต้องตรวจสอบว่าเป็น public certificate หรือ private key ก่อนจัดการ
3. music/, playlist/, runtime* ต้องรักษาข้อมูลเดิม
4. dist/ และไฟล์ .exe ต้องตรวจสอบว่าเป็น Release Artifact หรือไฟล์ทดสอบก่อนลบ
5. อย่าเพิ่งย้ายทุกอย่างตาม Target Structure จนกว่าจะตรวจสอบ imports, PyInstaller spec และ NSIS installer references
6. do not touch file in .gitignore
