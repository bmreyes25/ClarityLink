# Integration readiness

**Updated:** 2026-10-30
**Campaign:** CL-POLICY-02 revised engineering authorization
**Source base:** `origin/main` at `46039d90922e7bbe60c92aaa441d0ae8360e457e` (fetched for this policy amendment; includes merged PR #118)
**Offline development track:** `CUSTOM_INTEGRATION_RESEARCH_AUTHORIZED_OFFLINE`
**Vehicle deployment:** `VEHICLE_DEPLOYMENT_NOT_AUTHORIZED`. `safeForHonda()` remains `false`.

The owner authorizes Level A offline research/prototypes and Level B offline prototypes subject to technical design and safety/security review as defined in [vehicle testing and safety boundaries](../safety/vehicle-testing.md). This updates the development direction only. It does not grant OEM authorization or approve Honda installation, ADB, firmware/service replacement, cluster modification, vehicle-side display work, or connected-iPhone integration. Those remain separately gated by explicit owner authorization and qualified safety review. Preserve prior CL-OBS-02 observations and decisions as historical evidence; older reports reflect the more restrictive operating model in effect when written and are not retroactive records of this authorization.

| Boundary | Current evidence | Gate |
|---|---|---|
| Factory Type110 continuity | API17 lab result exists; reviewed static Honda path is Type110-only. No simultaneous approved target acceptance. | Lab PASS only; factory pass not established. |
| Genuine Honda Type111 receiver handoff | No supported capability, SETUP, session delegation, crypto context, data-port ownership, revocation, or teardown contract established in reviewed evidence. Offline custom receiver research is now permitted; no OEM authorization is established. | Historical gate `RECEIVER_AUTHORIZED_SPEC_REQUIRED` remains a vehicle deployment gate; it no longer bars offline research. |
| Honda Display 1 frame admission | No supported caller/admission contract, navigation geometry, page ownership, warning precedence, host-death handling, or restore contract established. Offline host-owned rendering investigation is now permitted. | Historical gate `DISPLAY_SUPPORTED_PATH_NOT_FOUND` remains a vehicle deployment gate; it no longer bars offline research. |
| API17 runtime/performance | CL-R4/R7 accepted; PR #52's exact-head API17 runtime, Offline CI, and CodeQL passed, but the controlled performance comparison missed its declared gates. | `PARTIAL`; full performance and reliability acceptance remain open. |
| Independent Type111 receiver | Step 43P is a PlayPort observation, not Honda evidence and not an approved bench acceptance for this campaign. | `AUTHORIZATION REQUIRED` for another live iPhone session. |
| Vehicle observation | Historical 43T0-D ended at zero targets before target commands. A prospective owner-assumed-risk exception is proposed for the fixed PR #118 C-P profile only. | `NOT AUTHORIZED` until protected-main policy adoption, exact Codex/Claude/ECC source-bound reviews and separate exact-run owner authorization. AI review is not human safety certification. |
| Synthetic Type111 lifecycle and disconnect fail-safe | Merged PR #92 adds a host-owned synthetic Display 1 lease/fail-safe model, including expiry and producer-stand-in death cases; merged PR #97 hardens fail-closed ingest and cleanup errors. | Offline synthetic evidence only. The full disconnect invariant and failure matrix remain incomplete; no Honda, real-iPhone, or complete factory-restoration behavior is established. |
| Restoration/reversibility | No complete target-specific restoration contract and independent recovery demonstration recorded. | Required before vehicle deployment; cluster firmware changes without independent recovery remain blocked for deployment. |
| Safety review | No independent vehicle-safety review for a target integration is recorded. | Required before any vehicle deployment/experiment. |
| Public/private preservation | Main status and reports are on GitHub; generated runtime evidence and Honda proprietary artifacts are private. | Verify private encrypted backup and restore independently; do not publish raw evidence. |

The two historical OEM-interface gates remain unresolved and must not be described as OEM permission. They no longer prevent offline custom integration research. Runtime admission, warning ownership, complete disconnect/recovery behavior, and independently verified restoration remain unestablished deployment blockers. A bench receiver or successful emulator cannot replace OEM authorization or vehicle acceptance. Do not claim the original vehicle goal is complete.

See [the dependency graph](../roadmap/master-dependency-graph.md), [acceptance gates](../roadmap/milestone-acceptance-gates.md), and [evidence ledger](evidence-ledger.md).
