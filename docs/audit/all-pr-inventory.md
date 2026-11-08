# All Pull Request Inventory — cvsz/autodj

Source: `gh api repos/cvsz/autodj/pulls?state=all&per_page=100` (full pagination, 140 PRs)
Baseline SHA: `9a5e829870d6cf11450a6ec56ff063f37aa616f8` (main == origin/main)

## Summary
- Total PRs discovered: **140**
- Pagination coverage: single page of 140 (complete; no further pages)
- Merged: **135**
- Closed without merge: **5**
- Draft: **3** (of which #4 and #101 were merged despite draft label)

Disposition counts:
- CLOSED_SUPERSEDED: 3
- DRAFT_INCOMPLETE: 1
- DUPLICATE: 1
- MERGED_VERIFIED: 135

## Full PR Inventory

| # | State | Draft | Disposition | Title | Base | Head | Merge SHA |
|---|---|---|---|---|---|---|---|
| #141 | closed | False | MERGED_VERIFIED | docs: sync final-report.md with latest enterprise validation results | main | docs/sync-final-report-20261108 | 9a5e829870d6cf11450a6ec56ff063f37aa616f8 |
| #140 | closed | False | MERGED_VERIFIED | docs: sync final-report.md with latest enterprise validation results | main | feat/final-report-tracking-20261108 | 9c20135d2c003eb51a8e12d51be93a1cd3c36065 |
| #139 | closed | False | MERGED_VERIFIED | docs: create final-report.md with full enterprise audit and remediation details | main | feat/final-report-20261108 | f92c5a457c9ddb2f3029d67437d483493eb9415f |
| #138 | closed | False | MERGED_VERIFIED | fix: remove 2>/dev/null suppression from YAML validation in auto-fix-loop | main | feat/fix-yaml-validation-suppression-20261108 | 74fcc58c4c37fd68fede72329a77492edf287a6f |
| #137 | closed | False | MERGED_VERIFIED | merge: integrate origin/main and unreleased v0.2.8 release commits into main | main | feat/merge-origin-main-20261108 | 8cddaa88a019619b84f10fba979cc30002c1a50f |
| #136 | closed | False | MERGED_VERIFIED | chore: merge AutoDJ v0.2.8 release | main | release/v0.2.8-production | 944396e59b12826937cd512c66e3af2ec9a5f308 |
| #135 | closed | False | MERGED_VERIFIED | chore: bump version to 0.2.8 | main | chore/bump-v0.2.8 | 255b3f59f59274f2679653c4c9c86f7ca731231e |
| #134 | closed | False | MERGED_VERIFIED | ci: download mpv from mpv.io direct link | main | fix/release-mpv-mpv-io | e07bddacd9bed4f73c836c1960e31ea182ca56ba |
| #133 | closed | False | MERGED_VERIFIED | ci: download mpv from official GitHub releases | main | fix/release-mpv-github-release | cb7bbc3274a9c480f32934d3415ce4e9dff831e4 |
| #132 | closed | False | MERGED_VERIFIED | ci: comprehensive mpv.exe search after Chocolatey install | main | fix/release-mpv-comprehensive-search | b8b5867b0fd886c3a92995f35272fa56f7c21d7c |
| #131 | closed | False | MERGED_VERIFIED | ci: add refreshenv and fallback paths for mpv Chocolatey install | main | fix/release-mpv-refreshenv | 6bd7f5a6a096f9cb7e5a8d3ac2b49c17ae3e3efc |
| #130 | closed | False | MERGED_VERIFIED | ci: use Get-Command to find mpv.exe after Chocolatey install | main | fix/release-mpv-getcommand | c0cef25cdf84d2de2472881655d704869df8fcf8 |
| #129 | closed | False | MERGED_VERIFIED | ci: fix mpv path detection for Chocolatey install | main | fix/release-mpv-path | 97382e37fc4b6a79eeda79d44769319ebeac6e40 |
| #128 | closed | False | MERGED_VERIFIED | ci: use Chocolatey to install mpv for release build | main | fix/release-mpv-choco | 708d3462cf1407436e0af089129d896921630ad1 |
| #127 | closed | False | MERGED_VERIFIED | ci: add mpv download step to release workflow | main | fix/release-mpv-download | ac305823cc3cbfdbc12054653e86770dfccb64c2 |
| #126 | closed | False | MERGED_VERIFIED | feat: Premium Enterprise UI + IM Auto-Reply + Auto-Reply System | main | feat/premium-enterprise-ui | 74c31de86b120b00f6ff5cfcba6d6bdb42072160 |
| #125 | closed | False | MERGED_VERIFIED | fix: make GUI dialogs and callbacks main-thread safe | main | fix/gui-thread-safety-main-thread | c92166fef9f0b884a430ce5721990223ef739ed2 |
| #124 | closed | False | MERGED_VERIFIED | fix: remediate enterprise audit findings — passphrases, invalid configs, output suppression | main | feat/autodj-enhancements-and-fixes | 88ccb3d0d63852e5d27b13c51a26bc86f2ac12e7 |
| #123 | closed | False | MERGED_VERIFIED | fix: harden workflows — address policedbc security review | main | feat/harden-workflows-v2-1794018678 | 40ed3fd6a2c88286284a93636b7d1736370f5fa9 |
| #122 | closed | False | MERGED_VERIFIED | fix: harden workflows for enterprise production grade | main | feat/harden-workflows-1794016028 | 091cf705291fbe64221b559068ea4941cef88309 |
| #121 | closed | False | CLOSED_SUPERSEDED | feat: add auto-fix open PRs workflow | main | feat/auto-fix-workflow-1793999659 | — |
| #120 | closed | False | CLOSED_SUPERSEDED | feat: add auto audit/review/approve workflow | main | feat/auto-audit-1793998118 | — |
| #119 | closed | False | MERGED_VERIFIED | feat: add auto audit/review/approve workflow | main | deploy-auto-audit-v2 | 991986a9ff73ad116f6230e867c4a34e97ca637c |
| #118 | closed | False | DUPLICATE | feat: add auto audit/review/approve workflow | main | deploy-auto-audit-workflow | — |
| #117 | closed | False | MERGED_VERIFIED | test: auto-audit workflow trigger v2 | main | test-auto-audit-v2-1793971178 | 66f0854c30f1bbc0ca49e117520f1e3e6094ee6c |
| #116 | closed | False | MERGED_VERIFIED | test: auto-audit workflow trigger | main | test-auto-audit-1793971120 | f1ce1bbea2e624209227e2dc6a6f8a439e7aab8e |
| #115 | closed | False | MERGED_VERIFIED | docs: mark placeholder Dockerfile checklist item VERIFIED | main | feat/autodj-enhancements-and-fixes | 9a0e0c85be4f39a48a980d124493fdfc8e076e4b |
| #114 | closed | False | MERGED_VERIFIED | build: add local audit image zpostgresql; fix release mypy gate; apply ruff format | main | feat/autodj-enhancements-and-fixes | 090461b58374e4bc57beebfac7712cf761647a13 |
| #113 | closed | False | MERGED_VERIFIED | feat: autodj enhancements and fixes | main | feat/autodj-enhancements-and-fixes | 80a7d2309bc98530dd4d15dbe90c9e4cd75dfc0c |
| #112 | closed | False | MERGED_VERIFIED | fix: security hardening — backup before repo overwrite, fail-closed admin authorization | main | fix/autodj-comprehensive-remediation-20261102-143019 | cbfaaed94d249acd11d371a965fd22f1cc63fcb8 |
| #111 | closed | False | MERGED_VERIFIED | style: remove unused noqa in __main__.py | main | style/remove-unused-noqa-main | a214465fd94e4f0d893c3f58670d91b074a6fe1c |
| #110 | closed | False | MERGED_VERIFIED | style: ruff format 12 files | main | style/ruff-format-12-files | 7f76abbda976cda66df254b0e1d3a105182925f8 |
| #109 | closed | False | MERGED_VERIFIED | fix: player music time countdown; fix settings dialog NameError; add input validation | main | fix/player-countdown-and-settings-dialog | d624ea2d0a9a1f7b633b410e4a9ae250d0e583e9 |
| #108 | closed | False | MERGED_VERIFIED | chore(deps): bump actions/attest-build-provenance from 2.4.0 to 4.2.2 | main | dependabot/github_actions/actions/attest-build-provenance-4.2.2 | 5cb15d496a063768147d77a4a8f1f6a4dde689fe |
| #107 | closed | False | MERGED_VERIFIED | chore(deps): bump actions/setup-python from 5.6.0 to 7.1.0 | main | dependabot/github_actions/actions/setup-python-7.1.0 | 6dc914a5d7fb824e0b7caa9f0154dd59170ba1df |
| #106 | closed | False | MERGED_VERIFIED | chore(deps): bump actions/checkout from 4.2.2 to 7.0.1 | main | dependabot/github_actions/actions/checkout-7.0.1 | 22d574127b16bdbd5c7f7055aa4fa11fdbc2555b |
| #105 | closed | False | MERGED_VERIFIED | docs: update Final-Report.md with all PRs merged status | main | docs/update-final-report-merged-prs | ace7f39db7c324e55fe6f966fc6fde8e575bdb86 |
| #104 | closed | False | MERGED_VERIFIED | fix(test): update upload-artifact SHA for v7.0.2 in release consistency test | main | fix/upload-artifact-v7-test-consistency | 69e6feb293098c070d0e50252c13d16d1edb440c |
| #103 | closed | False | MERGED_VERIFIED | docs: update Final-Report.md with release completion status | main | fix/sec-001-signing-integrity | 423f582a8d2196a5c5999f965c1badbd2b29e688 |
| #102 | closed | False | MERGED_VERIFIED | fix: player music time countdown; harden exception handling across modules | main | fix/sec-001-signing-integrity | 6f81ca7852e30ab86e33064d232e954ff0282fe7 |
| #101 | closed | True | MERGED_VERIFIED | fix(sec-001): remediate SEC-001 signing integrity and artifact lifecycle | main | review/sec-001-signing-integrity-20261104 | d6a755fc0603168e39f79c3ca3e0f0fd99b75220 |
| #100 | closed | False | MERGED_VERIFIED | fix(sec-001): remediate SEC-001 signing integrity and artifact lifecycle | main | fix/sec-001-signing-integrity | 33b088e8dc2aff4a0a16c8c584f9a9e396ac261c |
| #99 | closed | False | MERGED_VERIFIED | fix: remediate F-01 F-02 F-03 production defects | main | fix/test-and-ci-remediation | a4df182e7fcb9e0d81306af15db6c43813e1dbff |
| #98 | closed | False | MERGED_VERIFIED | fix(gui): show settings dialog content | main | fix/production-runtime-fixes | f1ea7fed4476e1cea2b5575bfa5c4a736bf3457f |
| #97 | closed | False | MERGED_VERIFIED | fix(gui): show remaining playback time countdown | main | fix/production-runtime-fixes | 6a53351dea8104f35b8a607c3e9db1f68d342c23 |
| #96 | closed | False | MERGED_VERIFIED | fix(test): fix Windows test compatibility issues | main | fix/windows-test-compatibility | ba0e2b2a4de27419c9bdde65e2036d3030eed68d |
| #95 | closed | False | MERGED_VERIFIED | fix(lint): cleanup ruff/mypy issues in migration code | main | fix/lint-cleanup | 8790cbccd9b540c977a6167ea46c164ecb080b7d |
| #94 | closed | False | MERGED_VERIFIED | fix(config): safe configuration migration for placeholder values | main | fix/config-migration-v2 | 18c15927eb641be631f619a4d7b666e0652dcda1 |
| #93 | closed | False | MERGED_VERIFIED | fix(config): safe configuration migration for placeholder values | main | fix/config-migration | 628472f7e4516d6ced0fd9cc933f2fa9e9a58701 |
| #92 | closed | False | MERGED_VERIFIED | fix(library): yt-dlp TLS trust integration - SSL fallback from exe to Python module | main | fix/tls-trust-integration | ffcc335c3b593f31e5dff66f1214ea3b78c24551 |
| #91 | closed | False | MERGED_VERIFIED | fix(ps-qualification-scripts): repair PowerShell 5.1 compatibility in qualification scripts | main | fix/ps-qualification-scripts | 3fdd722f84d6f8c33c0368199a92da5558a887f2 |
| #90 | closed | False | MERGED_VERIFIED | fix(library): correct yt-dlp CA bundle integration | main | fix/yt-dlp-ca-bundle | b45033270b92c83bccb78bf11b848092f56873f1 |
| #89 | closed | False | MERGED_VERIFIED | fix(production-runtime): add observability diagnostics and comprehensive regression tests | main | fix/production-runtime-remediation | 6834d52f1b7c11af52195e0b63285998e10abddb |
| #88 | closed | False | MERGED_VERIFIED | fix(production-runtime): complete P1/P2 remediation - gitignore installer artifacts, complete checklist, CI gating, doc rewrites, security hardening | main | fix/production-runtime-fixes | 2d3581b046103677685683705c1d3a45c654c197 |
| #87 | closed | False | MERGED_VERIFIED | qual: Windows Qualification Kit PowerShell script fixes | main | qual/windows-qualification-fix | 7d4e84ee094da9c205d2011a032e13a8dd8751f5 |
| #86 | closed | False | MERGED_VERIFIED | qual: Windows Qualification Kit | main | qual/windows-qualification-kit | 12f0d69545185df9b662bd945f6b3edbd82dd872 |
| #85 | closed | False | MERGED_VERIFIED | qual: production qualification acceptance reports | main | qual/production-acceptance | 4444636b8dbcbaa62c67bc9385ad6332d62102ca |
| #84 | closed | False | MERGED_VERIFIED | qual: production qualification reports and installer recovery fix | main | fix/production-qualification | 6baa8b7fcc47544eb21e3430e9f9db0124df81c6 |
| #83 | closed | False | MERGED_VERIFIED | ci: complete P0 hardening — SHA-pinned actions, release readiness reports | main | fix/pin-actions-shas | a837e0b70d48b4c28f0b209373e92f1bdd2592fe |
| #82 | closed | False | MERGED_VERIFIED | chore(deps): bump actions/upload-artifact from 4.6.2 to 7.0.2 | main | dependabot/github_actions/actions/upload-artifact-7 | 919cc41ed3c13575ab77441028d9fe89f14f5be5 |
| #81 | closed | False | MERGED_VERIFIED | chore(deps): bump actions/attest-build-provenance from 96b4a1ef7235a096b17240c259729fdd70c83d45 to e8998f949152b193b063cb0ec769d69d929409be | main | dependabot/github_actions/actions/attest-build-provenance-4 | 79faec96b9e22263d5f01b13c2d42733ef57fecc |
| #80 | closed | False | MERGED_VERIFIED | chore(deps-dev): update setuptools requirement from >=68 to >=84.2.1 | main | dependabot/pip/setuptools-gte-84.2.1 | b82bde018ccbe4dc7b8c347c96947645f0c1cdf6 |
| #79 | closed | False | MERGED_VERIFIED | security: remediate P1 and P2 findings (installer data safety, admin authorization, gated release) | main | fix/security-remediation-p1-p2 | 3b96e8da9adebca952f503df43fc26dc8b4a58bd |
| #78 | closed | False | MERGED_VERIFIED | fix: remove duplicate MUI_ABORTWARNING define from installer.nsi | main | fix/installer-nsi-final | 3be80e454a56f51e901239bf705836511b7d8006 |
| #77 | closed | False | MERGED_VERIFIED | checklist: mark all implementation checklist items complete | main | sync/implementation-checklist | 641c86144c0ddc46153c2e91a19258c5cdb35d99 |
| #76 | closed | False | MERGED_VERIFIED | fix: harden executable resolution and preserve user data | main | fix/autodj-executable-paths-release-gates | ff2d709b54e15d9ff97eb0e26227c1c815466e51 |
| #75 | closed | False | MERGED_VERIFIED | fix: remove duplicate MUI_ABORTWARNING define from installer.nsi | main | fix/installer-nsi-download-mpv | 641c86144c0ddc46153c2e91a19258c5cdb35d99 |
| #74 | closed | False | MERGED_VERIFIED | fix: remove duplicate MUI_ABORTWARNING define from installer.nsi | main | fix/installer-nsi-final | 575068fa6b0674c838d8b31850852fd2ee5bf3a4 |
| #73 | closed | False | MERGED_VERIFIED | fix: download mpv.exe from GitHub releases instead of bundling | main | fix/installer-nsi-download-mpv | bbabb2fb5ac452f0246a23f12faf39010373b9f0 |
| #72 | closed | False | MERGED_VERIFIED | fix: remove invalid MUI_ABORTWARNING define from installer.nsi | main | fix/installer-nsi-final-fix | 3985327d2619eefcac3a235b931514cd37149fee |
| #71 | closed | False | CLOSED_SUPERSEDED | fix: remove duplicate MUI_ABORTWARNING define from installer.nsi | main | fix/installer-nsi-vi-defines-final2 | — |
| #70 | closed | False | MERGED_VERIFIED | fix: remove invalid VI_* defines from installer.nsi | main | fix/installer-nsi-vi-defines | b1d6f516f87dc10c0012980fb9880da5ee64753e |
| #69 | closed | False | MERGED_VERIFIED | fix: remove invalid SetCompress line from installer.nsi | main | fix/installer-nsi-vi-defines | 89c5bdada31d59177c47c9a01a6caf190ab965ff |
| #68 | closed | False | MERGED_VERIFIED | fix: remove invalid VI_* defines from installer.nsi | main | fix/installer-nsi-vi-defines | 16cef312aa1f511dce8d95adc0099f0141c77fab |
| #67 | closed | False | MERGED_VERIFIED | feat: update yt-dlp.exe to latest version | main | fix/update-mpv-latest | 47193f3941cf73e9c438f0555a88acf2d73b4738 |
| #66 | closed | False | MERGED_VERIFIED | fix: add post-install mpv-register.bat and VBCABLE_Setup_x64.exe silent execution | main | fix/installer-nsi-post-install | 547c945fa2e7a53d283e273ec27e1a77d8a90a87 |
| #65 | closed | False | MERGED_VERIFIED | docs: update AutoDJ-Final-Report.md with residual risks, rollback, next actions | main | docs/final-report-update | 5c1c73f8dfa773226d3210af1165a3e95f6e4ad9 |
| #64 | closed | False | MERGED_VERIFIED | feat: bundle standard config.toml in NSIS installer | main | fix/installer-nsi-hardening | 5373f32dc224246dc124d6cbbf20d73635f3446b |
| #63 | closed | False | MERGED_VERIFIED | docs: add AutoDJ-Final-Report.md complete project report | main | docs/final-report | 9e25eae1172476f512d2f01799ed3fe3f3a01bc5 |
| #62 | closed | False | MERGED_VERIFIED | feat: add validate-template target to Makefile | main | chore/validate-template-target | 2e2d9925b96b8254b68bf2f448f01e7f2e53c6a0 |
| #61 | closed | False | MERGED_VERIFIED | chore: cleanup unused scripts and update github_admin default repo | main | chore/cleanup-unused-scripts | 0a4e473b2060baa03dfc75a8f13b6cb9898e1e83 |
| #60 | closed | False | MERGED_VERIFIED | fix: load folder button crash on permission-denied directories | main | fix/load-folder-crash | c1a25de6c92be4b51c61bc5b619e711ff232aa50 |
| #59 | closed | False | MERGED_VERIFIED | fix: protect log file creation against PermissionError on startup | main | fix/log-permission-clean | e171fa20be65daaca10cc97539822f1bffcbd42a |
| #58 | closed | False | MERGED_VERIFIED | fix: protect log file creation against PermissionError on startup | main | docs/v026-post-release-verification | 5a37467b4c8911361c43a97b26e43b39251e05a6 |
| #57 | closed | False | MERGED_VERIFIED | fix: settings config.toml write, hidden CMD launcher, type safety | main | docs/v026-post-release-verification | 80c7b6e4e38ad1524bd2878bb7127823d4c25680 |
| #56 | closed | False | MERGED_VERIFIED | fix: make playlist yt-dlp resolution TLS-safe across platforms | main | fix/playlist-ytdlp-tls-cross-platform | 572aad92e37285e7f89fdd16d52c1bb0918ead65 |
| #55 | closed | False | MERGED_VERIFIED | docs: add v0.2.6 release audit, security, acceptance and operational handover reports (#55) | main | docs/v026-release-documentation | 15a0f27d34990c16dd2ec03de2d2dc1ab7cf4541 |
| #54 | closed | False | MERGED_VERIFIED | chore: release Camfrog AutoDJ v0.2.6 | main | release/autodj-v0.2.6 | e2ec1013859e587b41dcd047a234b0cf14cd7580 |
| #53 | closed | False | MERGED_VERIFIED | docs: add v0.2.5 official release handover report (#53) | main | docs/v025-official-handover | 7ff20e10e2b88c39e0d56dd243e46b84587e1d1f |
| #52 | closed | False | MERGED_VERIFIED | docs: add v0.2.5 final release gate audit and acceptance report | main | docs/v025-release-gate-acceptance | 7387864948ed5d99c8140f6c6f2b2b12d9f3ac24 |
| #51 | closed | False | MERGED_VERIFIED | docs: add v0.2.5 baseline, release, and final verification reports | main | docs/v025-final-reports | c0e0f4bb07a0f213d4e6fdaba7a9a6eb32542a79 |
| #50 | closed | False | MERGED_VERIFIED | fix(ci): match installer artifact pattern Camfrog-AutoDJ-Setup-*.exe | main | fix/release-installer-filename | 78dc321d9584a7da5a1248ad057d7ac244045569 |
| #49 | closed | False | MERGED_VERIFIED | fix(ci): use cyclonedx-py environment with -o flag for SBOM generation | main | fix/release-sbom-flag | 4c7c4d366271bd3ab7726923d0128168181c2c4e |
| #48 | closed | False | MERGED_VERIFIED | fix(installer): mark external mpv and vbcable as nonfatal | main | fix/installer-optional-bundled-dependencies | c25d5daab60ef312f3a0d881d85f30c2e1630e75 |
| #47 | closed | False | MERGED_VERIFIED | fix(installer): make config.toml nonfatal in NSIS script | main | fix/installer-config-optional | 0f8f01613b83807a153fc302de68135efa65ad42 |
| #46 | closed | False | MERGED_VERIFIED | fix(ci): add NSIS to path for Windows release runner | main | fix/release-nsis-path-and-env | 7f3a6133cd258f95be324e116252d32a9341f875 |
| #45 | closed | False | MERGED_VERIFIED | feat: v0.2.5 audio fade, dynamic normalization, moderation, and SBOM attestation | main | feat/v025-product-enhancements | 2de86603c37359d8de2f159fead8d62ad0ad82a7 |
| #44 | closed | False | MERGED_VERIFIED | docs: sync playlist pack guidance and installer spec with 0.2.5 dynamic resolution | main | docs/sync-all-documentation | 264409ca584ddde4e854ebd5f909e17c87c3107a |
| #43 | closed | False | MERGED_VERIFIED | chore: bump and sync version 0.2.5 across docs, manifests, and build scripts | main | chore/sync-release-0.2.5-and-quality | 2c56583262a0ed3ca5d31f897c70c7db6ce7c78f |
| #42 | closed | False | MERGED_VERIFIED | feat: dynamic search resolution and lookahead preloading for playlist tracks | main | feat/dynamic-playlist-search-resolve | cd445da842ddc8fe6d20267f942c2fed1e069fa7 |
| #41 | closed | False | MERGED_VERIFIED | chore(deps): bump softprops/action-gh-release from 2 to 3 | main | dependabot/github_actions/softprops/action-gh-release-3 | 8116b4b8767877a36c99028a89e1025aaf5b60a0 |
| #40 | closed | False | MERGED_VERIFIED | fix(ci): align CodeQL action steps to v4.39.1 and configure dependabot group | main | fix/codeql-action-alignment-4.39.1 | 5e3c98281281b425c44ce76c2fdeebd3dde4d8d4 |
| #39 | closed | False | MERGED_VERIFIED | fix: resolve timeout and failure backoff edgecases in engine and player | main | fix/test-suite-and-playback-edgecases | ef8fbb63aa4b8e438c660c56273eb4b655a90c52 |
| #38 | closed | False | MERGED_VERIFIED | fix: gracefully handle missing join_uri_template in launcher | main | fix/join-uri-template-empty | 6984dd26b8d47855b7c283c5755de0f3f0d85319 |
| #37 | closed | False | MERGED_VERIFIED | fix: add window support to fake_tk for Settings tab scrollbar | main | fix/fake-tk-window-support | 6529667dd44dfd8cf5228e96c8675cbd824f04fe |
| #36 | closed | False | MERGED_VERIFIED | fix: fix NameError in auto_launch exception handler | main | fix/log-nameerror | 82d5e0616784bdfafda9b2506933680f4dcaaaee |
| #35 | closed | False | MERGED_VERIFIED | fix: fix NameError when auto_launch fails | main | fix/autolaunch-nameerror | 82d5e0616784bdfafda9b2506933680f4dcaaaee |
| #34 | closed | False | MERGED_VERIFIED | fix: auto-launch crash prevents GUI from opening | main | fix/autolaunch-gui | 7edc2fafb2217b361b6e63536074336fa14e0413 |
| #33 | closed | False | MERGED_VERIFIED | fix: bundle mpv.exe from system when mpv/ not in repo | main | fix/mpv-bundle-system | e549f4396a898d84f671503dbb92c7ff911eac45 |
| #32 | closed | False | MERGED_VERIFIED | fix: bundle mpv/ with AutoDJ.exe | main | fix/mpv-bundle | 25b24316d90130d21fa7c3d19876f85867dcc3c8 |
| #31 | closed | False | MERGED_VERIFIED | fix: log file directory not created | main | fix/log-file-directory | 15852ba7de3f73aa42620fba20a50a178a18bdaf |
| #30 | closed | False | MERGED_VERIFIED | fix: config.example.toml use relative mpv_path and ytdlp_path | main | fix/config-relative-paths | c624c32ded1b83b821662fe384cbdb269dff5b53 |
| #29 | closed | False | MERGED_VERIFIED | fix: include config.toml in installer | main | fix/config-permission | 1995dee9ba0571796438051f7fd5d044125a60a3 |
| #28 | closed | False | MERGED_VERIFIED | fix: config.toml PermissionError on Program Files install | main | fix/config-permission | 4ccc3caa8bd1d98cd58831197b148200afed25f0 |
| #27 | closed | False | MERGED_VERIFIED | fix: playlist not play when mpv not available | main | fix/playlist-not-play | aad516fbd482c90276de64b244acb9e32c0d586c |
| #26 | closed | False | MERGED_VERIFIED | fix: config.toml log_file PermissionError on Program Files install | main | fix/log-file-permission | 87130e1aeaef5a43418aa5e9ce060afa141a7af7 |
| #25 | closed | False | MERGED_VERIFIED | fix: Settings tab scrollbar - Save button was off-screen | main | fix/settings-scrollbar | b3b54183ca201010beef7755607332326d321e1e |
| #24 | closed | False | MERGED_VERIFIED | fix: NSIS installer config.toml read permission error | main | fix/nsis-config-read-permission | cf0a547dd4b788bae7f9dbf8cb129c063749050a |
| #23 | closed | False | MERGED_VERIFIED | fix: NSIS installer config.toml permission error | main | fix/nsis-config-permission | 3b7ce39430f245f5c848b286cec801e23da092bc |
| #22 | closed | False | MERGED_VERIFIED | feat: add Settings button to GUI header | main | feat/settings-button | 5760d21374cfad2d1483e56f0c8afcc8d4a85262 |
| #21 | closed | False | MERGED_VERIFIED | fix: NSIS installer CheckExistingInstall - remove StrReplace dependency | main | fix/nsis-uninstall-string | 74c5375583cf9d5a1bd6736c129e7fabdfd34d3e |
| #20 | closed | False | MERGED_VERIFIED | fix: NSIS installer CheckExistingInstall GetParameters error | main | fix/nsis-getparameters | dc62e888d1d9bd2f0c06d421908378f0fd6e17a4 |
| #19 | closed | False | MERGED_VERIFIED | feat: add Settings tab to GUI | main | feat/settings-tab | b7e7fd5af27660239ddd784dca8844330a0c9081 |
| #18 | closed | False | MERGED_VERIFIED | config: update config.example.toml for installer layout | main | config/installer-layout | df274f4175324e8659d16a47b16f74c68c546d8e |
| #17 | closed | False | MERGED_VERIFIED | fix: NSIS installer - auto-uninstall old version, add mpv + yt-dlp + VBCable | main | fix/nsis-installer-mpv-vbcable | 1de16816a136a6145ee0dd8f4952a233999324ed |
| #16 | closed | False | MERGED_VERIFIED | docs: sync CHANGELOG, README, Makefile with 0.2.5 release | main | docs/sync-release-0.2.5 | b7e2ae3b8d0e770b4b14545f225b96fc5043e955 |
| #15 | closed | False | MERGED_VERIFIED | docs: sync CHANGELOG, README, Makefile with 0.2.5 release | main | docs/sync-release-0.2.5 | fc141f055baca46b8fa559d74c34ef9acdba4389 |
| #14 | closed | False | MERGED_VERIFIED | fix: eliminate NSIS installer warnings, remove src section | main | fix/nsis-installer-warnings | 5bf8be42bbc7ae6876b703209cbf2fdd0116cc15 |
| #13 | closed | False | MERGED_VERIFIED | fix: eliminate NSIS installer warnings, remove src section | main | fix/nsis-installer-warnings | 2ab80db107c5da679e04512ed73b5b16d7cefd80 |
| #12 | closed | False | MERGED_VERIFIED | fix(ci): restore cross-platform test matrix | main | fix/restore-cross-platform-ci-20261031 | aaf8e4c9ce0dd82f9a4b10ba2d4fce3287877c34 |
| #11 | closed | False | MERGED_VERIFIED | chore: exclude build artifacts, binaries, debug scripts, forensic files | main | chore/gitignore-build-artifacts | 67ab32def58bd2c35bdacb426eee9ac8ad4d9042 |
| #10 | closed | False | MERGED_VERIFIED | chore: exclude build artifacts, binaries, debug scripts, forensic files | main | chore/gitignore-build-artifacts | 3c4aad18a14ffaf203f08d90718f6717e1b42007 |
| #9 | closed | False | MERGED_VERIFIED | release: v0.2.4 enterprise production fixes | main | fix/enterprise-production-fixes | 8d3feaee52b921fd57dd0b8f6200b8f8c3974266 |
| #8 | closed | False | MERGED_VERIFIED | Fix tracks stopping before completion | main | fix/play-tracks-to-completion | a5ef96ea37b2620519f8d21307d89d483d0919e1 |
| #7 | closed | False | MERGED_VERIFIED | build(deps): bump actions/setup-python from 5 to 7 | main | dependabot/github_actions/actions/setup-python-7 | 1617dddd261009f969039c5ff571e0d1316f540a |
| #6 | closed | False | MERGED_VERIFIED | build(deps): bump actions/checkout from 4 to 7 | main | dependabot/github_actions/actions/checkout-7 | ef8f7012a71c4e815baeaa59523c947668df805e |
| #5 | closed | True | DRAFT_INCOMPLETE | fix(ci): restore deterministic AutoDJ test baseline | main | fix/autodj-test-baseline-20261028-run11 | — |
| #4 | closed | True | MERGED_VERIFIED | fix(ci): align CodeQL action versions | main | fix/codeql-actions-version-alignment-20261028-run11 | ac54ce3ddbe0dfd654617ee14be68ce49f791321 |
| #2 | closed | False | MERGED_VERIFIED | chore(deps): bump github/codeql-action/init from 4.38.2 to 4.39.1 | main | dependabot/github_actions/github/codeql-action/init-4.39.1 | 2614b570b821474c0b24d9d38c85eca6232895ab |
| #1 | closed | False | MERGED_VERIFIED | chore(deps): bump github/codeql-action/analyze from 4.38.2 to 4.39.1 | main | dependabot/github_actions/github/codeql-action/analyze-4.39.1 | f6dbde9541c0a54dcbfc6bc97265086b3499441b |
