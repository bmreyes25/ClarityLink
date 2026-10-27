# Active blockers — CL-MASTER-01

**Updated:** 2026-10-20. Detailed evidence is in the [integration readiness](integration-readiness.md), [evidence ledger](evidence-ledger.md), and [acceptance gates](../roadmap/milestone-acceptance-gates.md).

| Blocker | State | Required resolution | Milestone |
|---|---|---|---|
| Honda Type111 receiver ownership | **UNRESOLVED for vehicle deployment** | Authorized versioned contract for same-session Type111 advertisement, accepted SETUP, authentication/session ownership, authoritative configuration, transport, revocation and teardown is still absent. `RECEIVER_AUTHORIZED_SPEC_REQUIRED` remains a deployment gate; offline custom receiver research is authorized. | CL-IF-01 / CL-POLICY-02 |
| Honda Display 1 frame admission | **UNRESOLVED for vehicle deployment** | Supported caller/frame contract, physical Navigation geometry, page ownership, warning priority, stale-frame withdrawal, host restart and factory restoration are still absent. `DISPLAY_SUPPORTED_PATH_NOT_FOUND` remains a deployment gate; offline host-owned rendering research is authorized. | CL-IF-01 / CL-POLICY-02 |
| CL-R12-F full API17 acceptance | **PARTIAL** | PR #52 merged with passing exact-head API17 runtime, Offline CI, and CodeQL checks, but its controlled performance comparison missed the declared gates; complete fault matrix, stage timing, process-resource evidence, and post-destruction cleanup remain open. | CL-R12-F |
| CL-R13-A canonical publication | **IN PROGRESS** | Complete exact-range review and merge PR #53 through normal project rules. Current CI/CodeQL passes; no approval is recorded. | CL-R13-A |
| CL-R11-A / CL-R12-B/C/D/E report reconciliation | **NOT RECONCILED** | Locate authoritative report/version/commit and evidence class, preserve limits, and update the ledger without importing unpublished work. | CL-IF-01 / CL-R12-F |
| Private evidence backup/recovery | **UNVERIFIED** | Verify encrypted archive backup and recovery in authorized private storage; publish only a sanitized receipt. No PASS is claimed here. | CL-MASTER-01 |
| Independent target safety review | **NOT RECORDED** | Obtain review of exact target integration, warning behavior, stop conditions and rollback before any target-facing work. | CL-INT-01 / CL-VT-01 |
| Separate live-iPhone / vehicle authorization | **NOT AUTHORIZED** | Offline R&D permission does not authorize a connected-iPhone test, bench session, or vehicle observation. Each needs its own exact scope, independent review, explicit owner approval, privacy plan, and stop/rollback conditions. | CL-REC-01 / CL-OBS-01 / CL-VT-01 / CL-POLICY-02 |
| Honda vehicle acceptance | **NOT STARTED** | Requires supported contracts, integrated lab acceptance, safety review, reversible procedure, exact authorization, and all vehicle-relevant F1–F12 evidence. F13 (public development history) is tracked separately and is not a vehicle-test prerequisite. | CL-VT-01 |

CL-R4 and CL-R7 remain **API17 LAB PASS** within their recorded synthetic scope. Historical FinalizerWatchdogDaemon behavior remains **NOT REPRODUCED** and unattributed. `safeForHonda()` remains `false`.
