# Active blockers — CL-MASTER-01

**Updated:** 2026-10-21. Detailed evidence is in the [integration readiness](integration-readiness.md), [evidence ledger](evidence-ledger.md), and [acceptance gates](../roadmap/milestone-acceptance-gates.md).

| Blocker | State | Required resolution | Milestone |
|---|---|---|---|
| Honda Type111 receiver ownership | **BLOCKED / UNKNOWN** | Authorized versioned contract for same-session Type111 advertisement, accepted SETUP, authentication/session ownership, authoritative configuration, transport, revocation and teardown; otherwise record NO-GO. | CL-IF-01 |
| Honda Display 1 frame admission | **BLOCKED / NOT ESTABLISHED** | Supported caller/frame contract, physical Navigation geometry, page ownership, warning priority, stale-frame withdrawal, host restart and factory restoration; otherwise record NO-GO. | CL-IF-01 |
| CL-R12-F full API17 acceptance | **PARTIAL** | Complete original scenario, stage timing, controlled A/B, ten reconnect cycles, remaining failure matrix, predeclared performance gates, clean teardown, and exact-head CI. PR #52 merged, but the measured result misses the 27 FPS and p95 ≤50 ms thresholds; ≤10% drops and complete failure/resource/soak evidence are also outstanding. | CL-R12-F |
| CL-R13-A canonical publication | **IN PROGRESS** | Complete exact-range review and merge PR #53 through normal project rules. Exact-head `offline-tests` and CodeQL pass after the branch sync; no independent review is recorded. | CL-R13-A |
| Honda research publication (#53, #65, #67–#69) | **REVIEW PENDING** | Public reports exist on PR branches; #66 is merged. GitHub metadata still reports stale heads/base on #53/#65/#67 although repository branch refs have newer commits. Complete independent privacy, provenance and accuracy review and reconcile refs before merge. | CL-R13-A / CL-HH-06 / CL-HH-07 / CL-IF-01 / CL-GH-06 |
| CL-R11-A / CL-R12-B/C/D/E report reconciliation | **NOT RECONCILED** | Locate authoritative report/version/commit and evidence class, preserve limits, and update the ledger without importing unpublished work. | CL-IF-01 / CL-R12-F |
| Private evidence backup/recovery | **UNVERIFIED** | Verify encrypted archive backup and recovery in authorized private storage; publish only a sanitized receipt. No PASS is claimed here. | CL-MASTER-01 |
| Independent target safety review | **NOT RECORDED** | Obtain review of exact target integration, warning behavior, stop conditions and rollback before any target-facing work. | CL-INT-01 / CL-VT-01 |
| Separate live-iPhone / vehicle authorization | **NOT AUTHORIZED** | A bench session or read-only vehicle observation needs its own exact scope, independent review, explicit owner approval, privacy plan, and stop/rollback conditions. | CL-REC-01 / CL-OBS-01 / CL-VT-01 |
| Honda vehicle acceptance | **NOT STARTED** | Requires supported contracts, integrated lab acceptance, safety review, reversible procedure, exact authorization, and all vehicle-relevant F1–F12 evidence. F13 (public development history) is tracked separately and is not a vehicle-test prerequisite. | CL-VT-01 |

CL-R4 and CL-R7 remain **API17 LAB PASS** within their recorded synthetic scope. Historical FinalizerWatchdogDaemon behavior remains **NOT REPRODUCED** and unattributed. `safeForHonda()` remains `false`.
