# Repository organization and GitHub health review

**Scope:** offline repository documentation, navigation, privacy, and workflow maintenance. This is not a numbered vehicle milestone. No Honda, ADB, vehicle collector, Type111 runtime, proprietary firmware, or private capture was used.

## Starting state and preservation

- Starting HEAD: `00511312b60845656b5e656aaa294189dc8afefd`, clean `main`, synchronized with `origin/main` after a read-only fetch.
- The repository was already organized into `src/`, `tests/`, `tools/`, `docs/`, `research/`, `step-reports/`, `simulator/`, and `demo/`. Those top-level engineering trees remain in place.
- No tracked research file or milestone report was moved or deleted. Historical negative results, findings, and evidence were not rewritten; a previously published private vehicle endpoint was redacted from the current tree in 16 historical text files. No source implementation, protocol behavior, evidence classification, or `jmcs` binary was changed.
- Root working-state records remain at their established paths. Curated landing pages and current summaries point into them.

### Initial tracked-tree inventory

| Area | Tracked files | Audience / role |
|---|---:|---|
| Root files | 9 | Public README, contribution guide, roadmap, and expert/current-state ledgers. |
| `.github/` | 5 | Offline CI, pull-request template, and three structured issue forms. |
| `docs/` | 7 | Curated architecture, development, and research guides. |
| `research/` | 406 | Detailed technical studies, source/evidence records, plans, and preserved artifacts. |
| `step-reports/` | 109 | Chronological milestone history and support files. |
| `src/` | 64 | Models, parsers, utilities, and adapter contracts. |
| `tests/` | 49 | Synthetic/host-side verification and test fixtures. |
| `tools/` | 20 | Test runner, offline analyzers, dry runs, and gated collector tools. |
| `demo/`, `simulator/` | 6 | Offline demo and digital-twin material. |

The starting inventory totals **675 tracked files**, including 427 Markdown files. Private/ignored and generated files are not part of this inventory. Visitor entry points were README/docs and existing contribution forms; current-state records were the root ledgers; research and step reports were the detailed and historical records. No mass moves were justified.

## File accounting

Added:

- `SECURITY.md`, `.github/dependabot.yml`, `.github/workflows/codeql.yml`.
- `docs/glossary.md`, `docs/safety/vehicle-testing.md`, and `docs/project/records.md`, `docs/project/license-decision.md`, `docs/project/github-settings.md`.
- `src/README.md`, `tests/README.md`, `tools/README.md`, `tools/check_repo_health.py`.
- This maintenance report.

Updated: `README.md`, `ROADMAP.md`, `NEXT_ACTION.md`, `PROJECT_STATE.md`, `EVIDENCE_INDEX.md`, `docs/README.md`, `docs/research/honda-type111-research-plan.md` (heading level only), `research/README.md`, 16 historical acquisition/capture/research/report text files (private endpoint redaction only), `research/acquisition/TERMINAL_RESUME_GUIDE.md` (superseded banner and personal repository path redaction), `step-reports/README.md`, `step-reports/21-runtime-read-design.md` (broken relative link only), `.gitignore`, `.github/workflows/ci.yml`, `.github/pull_request_template.md`, and the existing bug, research, and vehicle-test issue forms.

Moved: **0**. Removed: **0**. Historical step reports, detailed research, source trees, tests, tools, and generated/private evidence locations were intentionally left in place.

## Findings and changes

| Area | Review result |
|---|---|
| README | Rebuilt as a concise project front door: goal, honest status table, evidence classes, architecture, boundaries, quick offline demo/tests, four reader paths, repository map, and license status. |
| Documentation hierarchy | Upgraded `docs/README.md`; added glossary, vehicle safety guide, project-records guide, GitHub settings checklist, and license decision note. Existing architecture/development guides were retained. |
| Research index | Reorganized by technical domain and reader task; added a small set of verified starting links. Deep research stays in place. The old host-specific acquisition terminal guide is clearly marked as superseded and points to current project gates; its historical command/path text is preserved. |
| Step-report index | Replaced stale 43S-current claims with current PREP2/D4 status, latest reports, milestone eras, and a complete collapsible archive. Historical NO_GO and stop reports remain accessible. |
| Current status | `PROJECT_STATE.md` now opens with 43T1-PREP2 status, known blocker, one next action, and latest report. `NEXT_ACTION.md` has one current action and labels prior actions as historical. `ROADMAP.md` no longer calls 42K current. |
| Source/test/tool navigation | Added `src/README.md`, `tests/README.md`, and `tools/README.md` with offline/host-only and vehicle-facing boundaries. |
| Community health | Added `SECURITY.md`; strengthened existing issue and PR templates without making routine PRs vehicle-heavy. Blank issue creation remains available. |
| License / citation / conduct | No license chosen. No `CITATION.cff` added because an author identity suitable for citation was not verifiable from public project metadata. No Code of Conduct added because no enforceable public conduct-reporting contact was established. Owner decisions are recorded here and in the linked guides. |
| Dependencies / code scanning | Added weekly Dependabot version checks for the actually used pip and GitHub Actions ecosystems. Added a CodeQL workflow for Actions, C/C++, Java, JavaScript/TypeScript, and Python. Updated checkout/setup actions to the current major releases to address the runner's Node 20 deprecation warning; hosted results are pending verification. |
| GitHub metadata/settings | Description and six existing focused topics were verified and left unchanged. Default branch `main`, public visibility, and Issues enabled were verified. Dependabot updates are enabled and the alerts API query returned zero. Secret scanning, push protection, and private vulnerability reporting are verified disabled; default code scanning is not configured; `main` has no branch protection. Owner actions are listed in `docs/project/github-settings.md`. |

## Repository and privacy audit

- The initial inventory had 675 tracked files, 427 Markdown files, and 107 milestone/support Markdown files eligible for the step-report index (excluding `README.md` and `RUN_STATUS.md`). The tracked root organization remains intact; the working tree contains 688 files and 437 Markdown files before commit.
- Before editing, one broken relative Markdown link was found in `step-reports/21-runtime-read-design.md`; it was corrected. In a clean tree containing only Git-tracked files, 67 relative references originally pointed to unavailable/untracked artifacts; 66 historical references remain outside the curated-link CI scope because they point to ignored/private or unpublished source material. Curated public docs have **0** broken relative links. The initial step-report index linked 77 of 107 eligible files and incorrectly called 43S current; the new index links all 108 eligible files, including this maintenance report.
- Orphan count is measured mechanically as tracked Markdown files with no inbound repository-relative Markdown link. The count fell from **144 to 138** after navigation changes. These are candidates only, not presumed deletions; detailed technical and historical records are intentionally retained.
- Tracked extension/path audit found no committed APK, DEX/ODEX, shared library, firmware image, binary archive, or raw packet-capture file. Redacted/sanitized research summaries and explicit capture plans remain tracked as text/structured evidence. Existing strict `.gitignore` rules were preserved, extended to exclude common packet/raw-capture extensions, and narrowly extended to permit the checker and its tools index.
- Synthetic material is visibly marked in the offline demo and tests; private/raw capture, decompiled, and extracted artifact locations remain ignored. No code, research, or report orphan was deleted. The 138 no-inbound-link Markdown candidates were reviewed as archive/navigation candidates and kept; current curated docs now link the principal architecture, safety, evidence, demo, and contribution paths.
- No duplicated index was introduced: `docs/README.md` is the audience/task hub, `research/README.md` is the deep-research map, and `step-reports/README.md` is the dated milestone archive. No current guide needed a supersession banner; the inaccurate current-status wording was fixed at its navigation source instead of rewriting old reports.
- Visitor-facing current docs were checked for private `/Users/...` dependencies. The superseded acquisition terminal guide's personal repository path was also redacted. Other historical local-path references were retained; no Git history was rewritten. The older published endpoint was removed from the current tree in 16 historical text files without changing the surrounding findings. Two synthetic network-config test fixtures retain their test addresses; no current operational document contains the endpoint.
- Description/topics were reviewed read-only. No metadata mutation was made.

## Health checks and CI

`tools/check_repo_health.py` performs local-only checks: required navigation paths, tracked Markdown relative links, full step-report index coverage, forbidden binary/capture extensions, and personal absolute paths in visitor-facing docs. It does not use the network or contact Honda. Offline CI runs it before the existing project suite. The existing Offline CI test command and coverage remain intact.

Verification performed locally:

- `tools/check_repo_health.py`: **PASS** — 437 Markdown files; 108/108 milestone/support reports indexed; 0 curated-doc broken links; 0 forbidden file extensions; 66 historical/untracked references explicitly outside CI's public-navigation scope.
- YAML syntax for the three issue forms, Dependabot, Offline CI, and CodeQL: **PASS**. Visitor-facing Markdown H1 checks, personal-path check, and `git diff --check`: **PASS**.
- Tracked proprietary/private-file audit: **0** forbidden binary/archive/capture extensions and **0** binary content detected; no tracked private captures, APK/DEX/ODEX/shared libraries, firmware image, or archive found.
- The staged change removes the older published vehicle endpoint from the current tree; no endpoint value is repeated in this report. A full tracked-tree scan found token/key patterns nowhere; MAC-shaped strings occur only in synthetic redaction tests. Two network-config unit tests retain synthetic private-range fixture values. Current visitor-facing documents contain no absolute personal path. Deeper historical notes retain old local-path references and Git history was not rewritten, so prior revisions remain unchanged.
- Configured `tools/run_tests.sh`: **642 passed, 3 skipped**. Self-locator smoke: **3/3 passed**. Three simulator contract scripts and the Type111 failure-twin script passed. Native C host checks ran in the Python suite. The configured skips remain capability/private-data related; there was no live Honda/ADB/runtime test.

The implementation was pushed to `main` as `8d6fa23324a07372ff4b2d3025a2e5eb59462d70`. For that commit, [Offline CI run 37098342998](https://github.com/bmreyes25/ClarityLink/actions/runs/37098342998) passed, including repository health and the existing offline suite; [CodeQL run 37098342950](https://github.com/bmreyes25/ClarityLink/actions/runs/37098342950) passed for Actions, C/C++, Java/Kotlin, JavaScript/TypeScript, and Python. No runtime evidence is claimed by this documentation maintenance pass.

## ECC-guided review and remaining owner actions

Applied ECC security-review and coding-standards guidance manually. Review scope includes privacy boundaries, relative-link and index validation, least-privilege workflow permissions, offline checker behavior, vehicle-tool discoverability, and whether the new policies state only verified repository settings. No independent ECC reviewer endpoint was available; this is not an independent audit.

Manual owner follow-ups: choose an appropriate license after reviewing content ownership; consider adding a Code of Conduct and public enforcement contact; enable secret scanning, push protection, and private vulnerability reporting; decide on `main` protection requiring Offline CI/review; review CodeQL alert availability, action allowlisting, and SHA pinning. No GitHub owner-level settings were changed.

**Vehicle boundary:** this pass does not authorize Honda contact, ADB, Type111 negotiation, RAM attachment, or any modifying vehicle test. The current next vehicle milestone remains a separately initiated read-only 43T0-D/D4 network observation under its reviewed gates.
