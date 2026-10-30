# CL-MASTER-01 — end-to-end Type111 Honda integration program

> **PRIMARY GOAL: iPhone-origin Type111 secondary CarPlay video on factory Display 1, simultaneous with normal Type110 on Display 0.** Canonical statement and traceability matrix: [primary goal](../project/primary-goal.md). It takes precedence over any ambiguous wording below.

**Owner objective:** determine whether genuine, simultaneous Apple CarPlay can remain normal on the 2018 Honda Clarity factory center display while genuine iPhone-provided secondary CarPlay video, carried on Type111, appears in the cluster Navigation area, without compromising factory instruments, warnings, Navigation ownership, or restoration.

**Project status:** the objective is not yet established as feasible. The lab result is not a Honda integration. The master plan is a sequence of evidence gates, not vehicle authorization. `safeForHonda() == false`.

## Canonical records

- [Finish-line contract F1–F13](finish-line-definition.md)
- [Master dependency graph](master-dependency-graph.md)
- [Campaign acceptance gates](milestone-acceptance-gates.md)
- [Evidence ledger](../status/evidence-ledger.md)
- [Campaign issue index](../status/campaign-issues.md)
- [Integration readiness](../status/integration-readiness.md)
- [Public/private evidence boundary](../security/public-private-evidence-boundary.md)
- [Vehicle safety gates](../security/vehicle-safety-gates.md)
- [Campaign tracker issues](../status/campaign-issues.md) (ten canonical campaign issues)
- [Reference-library status](../research/cl-master-01-reference-status.md) (existing CL-R13-A work is in PR #53; do not duplicate it)

## Phase plan

| Phase | Campaign / objective | State and exit condition |
|---|---|---|
| 0 — Establish current state | Record repository, current main, dirty worktrees, open PRs, protections, and published versus local-only evidence. | **Recorded for this plan:** main base `c30a385455449b3c1d7b5cc65bb74c88c694b7f8`; current PRs #53, #52, #19, #7; no issues existed at discovery. Active source worktree `cl-r4-reliability-completion` was left untouched with private untracked research preserved. |
| 1 — Define finish line | Specify F1–F13, proof class and non-equivalent evidence. | **Done in plan:** [finish-line contract](finish-line-definition.md). No F-item is passed for Honda. |
| 2 — Reconcile evidence | Link R4–R13, R10A/B/C, R11-A, R12-B/C/D/E, 43P, 43T0, HondaHack, and private evidence classes with claim limits. | **Partial:** [ledger](../status/evidence-ledger.md) links public evidence and open PRs. CL-R11-A and R12-B/C/D/E require report-level reconciliation; private archive recovery is not verified. |
| 3 — REA / xcertplay references | Pin tools/source, describe Codex/JADX/JDK/Ghidra setup, protocol paths, security and GPL-3.0 boundaries. | **In progress in PR #53:** no duplicate research campaign; close that existing work and review. See [reference status](../research/cl-master-01-reference-status.md). |
| 4 — HondaHack reconstruction | CL-HH-06, offline and sanitized architecture map. | **Not started.** Requires lawful offline source/artifact and private/public boundary. No vehicle or installed-package changes. |
| 5 — Factory Android architecture | CL-SYS-01, bounded ownership, process/Binder/native/display and risk maps from authorized preserved artifacts. | **Not started.** Static analysis only until separately scoped authorization. |
| 6 — Restore API17 lab | CL-R12-F original scenario, timing, controlled A/B, ten reconnects and remaining failure matrix. | **Partial, PR #52 merged:** exact-head API17 runtime, Offline CI, and CodeQL passed; the controlled performance comparison missed its declared gates and full reliability criteria remain incomplete. See [runtime plan](../development/api17-runtime-recovery.md). |
| 7 — Authenticated bench Type111 | CL-REC-01, independent legitimate receiver and a separately authorized live-iPhone session. | **Blocked pending separate scope and approval.** It does not prove Honda compatibility. |
| 8 — Establish Honda contracts | CL-IF-01 receiver session/SETUP and cluster admission/geometry/warnings/restore. | **Blocked / critical path.** Any unsupported or ambiguous boundary means NO-GO. |
| 9 — Gated read-only observations | CL-OBS-01 only for a precise unresolved question that private offline artifacts cannot answer. PR #118 supplies the separate fixed C-P profile for its exact passive question. | **C-P review/run authorization pending; not authorized to run.** The exact human artifact is not verified and separate owner authorization is pending. All other observations need their own exact allowlist, qualified review, owner approval and recovery boundary. |
| 10 — Integration implementation | CL-INT-01 final integration remains gated; CL-INT-04 is the next offline/API17 withdrawal milestone under issue #62. | **Offline CL-INT-04 may proceed under merged CL-POLICY-02. Honda/vehicle integration remains blocked** until contracts, lab gates, separate authorization, and safety review pass. No speculative firmware, Xposed, or private Binder replay. |
| 11 — Vehicle acceptance | CL-VT-01 future conditional acceptance against F1–F13. | **Not authorized.** Requires reversible procedure, exact approval, independent safety review, and parked-only stop criteria. |
| 12 — Alternative architecture | CL-REL-01 if a required stock interface is unsupported or target acceptance is NO-GO. | **Conditional.** Explain tradeoffs; do not call a separate receiver/external display the original finish line. |
| 13 — GitHub documentation system | Keep public-safe source of truth, issue links, reports, status, provenance and reproducibility. | **This PR supplies the initial structure.** Update status only with evidence; do not rewrite historical decisions/approvals. |
| 14 — GitHub tracking | One issue per planned campaign unless an equivalent issue exists. | **Complete:** ten canonical issues #55–#64 are linked in the [campaign issue index](../status/campaign-issues.md). |
| 15 — Execution discipline | Read instructions, roadmap, issue, dependencies; define acceptance; evidence; verify; update ledger/status; commit/push/PR; report. | **Required for every subsequent campaign.** Do not repeat completed research or bypass review. |
| 16 — Verify plan | Check dependency order, safety consistency, evidence classes, links, JSON, health, whitespace, secret/private artifact boundary, independent reviews. | **Pre-publication validation is required.** No historical approval is manufactured. |
| 17 — Publish | Feature branch from current main, exact remote SHA, PR, CI/CodeQL/review state and links verified. | **PR #54 is open** from the recorded main SHA; verify required checks and review state before considering publication complete. Do not merge or auto-merge; leave open if required review is unavailable. |

## Current evidence and blockers

### Kickoff repository snapshot

- Repository: `bmreyes25/ClarityLink`; current `origin/main` fetched and recorded at `c30a385455449b3c1d7b5cc65bb74c88c694b7f8`.
- The active source worktree was `cl-r4-reliability-completion`, branch `cl-r4-reliability-completion`, HEAD `6e92d40d5cd884f76035442d9e85215e532a218f`. Its initial status had two untracked private research items and no ahead/behind count against its tracking branch; those files and the checkout were preserved unchanged. Other campaign worktrees were not incorporated.
- Roadmap work is isolated on `docs/cl-master-01-type111-program`, created clean from the recorded `origin/main` SHA. No historical branch was merged or rewritten.
- GitHub had open PRs #53, #52, #19 and #7, and no issues at discovery. PR #53 checks passed with no approval; PR #52 had an Offline CI failure while its API17 smoke and CodeQL checks passed. Other PRs were left untouched.
- `main` has an active ruleset named **Protection is key**: deletion and non-fast-forward updates are blocked, and `offline-tests` plus `CodeQL` are required. The configured approving-review count is zero; this does not waive the project rule against self-merging safety-sensitive work or the independent review required by campaign workflow.

The [CL-R4/R7 API17 lab](../status/current.md) demonstrates the synthetic pipeline only. The bounded Honda static record identifies a main Type110 path and no supported Type111 delegation or arbitrary-frame Display 1 contract in the reviewed paths. The separate PlayPort observation is a saved third-party lab result, not Honda proof. PR #92's host-owned lease/fail-safe, PR #94's Type111 ingest, and PR #97's ingest hardening are merged synthetic/offline work; none establishes Honda behavior or iPhone-origin video in ClarityLink. CL-R12-F remains partial after PR #52 merged: its performance comparison missed declared gates. CL-R13-A / PR #53 remains open with passing checks and no approval recorded.

Critical blockers:

1. An authorized, versioned Honda receiver contract for same-session Type111 admission, security/session ownership, config, transport and revocation.
2. A supported, authorized Honda Display 1 frame-admission contract including physical geometry, Navigation ownership, warning priority, withdrawal, host failure and restoration.
3. Full, reproducible API17 runtime/performance acceptance and exact-head CI.
4. Independent review and separate owner authorization for any bench-iPhone or vehicle activity.
5. Verified encrypted private evidence backup/recovery; this document makes no such claim.

## Next authorized offline milestone

**CL-INT-04 — autonomous host-owned Display 1 withdrawal**, tracked under existing issue [#62](https://github.com/bmreyes25/ClarityLink/issues/62). This follows merged policy PR #91 and reuses merged fail-safe, Type111 ingest, and error-handling infrastructure from PRs #92, #94, and #97. Implement and verify:

1. Host-owned timer/lease expiry and Display 1 withdrawal without producer `tick()`.
2. Producer-process death handling and stale-generation fencing.
3. Type110 independence during Display 1 withdrawal and restart.
4. Safe host restart and teardown with accurate cleanup-failure reporting.
5. Actual Android API 17 emulator runtime verification of expiry, process death, restart, teardown, and recovery.

Keep this stage offline, synthetic, and fail-closed. Do not use Honda/ADB, a vehicle, firmware, or a connected iPhone. Keep `safeForHonda() == false`; do not claim Honda compatibility, OEM authorization, iPhone-origin Type111 handling, or physical Display 1 output. CL-INT-04 is a withdrawal prerequisite, not completion of the primary goal.

## Public-safe campaign report standard

Every campaign report states: objective; baseline; sources/versions; method; findings; evidence class; receipts; limits; security implications; public/private boundary; decision; blockers; next task; acceptance criteria; commit and PR. Public-source publication never includes Honda firmware/APKs, raw decompilation, private addresses or hook recipes, vehicle captures/identifiers, certificates/keys, credentials, private research bundles, or sensitive machine configuration.
