# CL-FACTORY-01 — Factory integration research & engineering index

Canonical public-safe entry point for the factory-integration campaign (Claude-owned). Shared with Codex.
Branch: `claude/cl-factory-01-architecture`. Base: `origin/main` `115ca976891daf95fd665f72d360dae19cceb111`.
Scope: offline, static, synthetic. No vehicle/ADB/live-iPhone. `safeForHonda() == false` (unchanged).

## Objective (engineering framing)
Advance an **independent, fail-closed compatibility layer** that could, in principle, deliver a secondary CarPlay
("Type111") navigation stream to the instrument-cluster Navigation area while factory Type110 CarPlay continues on
the center display — *without* assuming entitlement to the factory session, cluster host, or authentication. Where
genuine integration requires authorized receiver hardware/authentication or unproven host contracts, that is
reported as a blocker, and only the independently testable offline components are implemented.

## Evidence classes
`PROVEN_STATIC` (current inspected artifact), `PRIOR_SAVED_RUNTIME` (historical snapshot), `INFERRED` (bounded),
`UNKNOWN`, `SYNTHETIC` (lab/offline only — never promoted to factory evidence).

## Milestones
| M | Title | Status |
|---|---|---|
| M1 | Factory artifact & build-compatibility verification | **COMPLETE** (reports 01, 02) — inventory + deodex pipeline verified |
| M2 | CarPlay receiver + Type110 reconstruction | **IN PROGRESS** (report 03) — Java/native graph recovered; native locus + AIDL fabric mapped |
| M3 | Factory Navigation + Display 1 architecture | **IN PROGRESS** (reports 06,07,08) — structured-data flow + two-layer warning composition mapped |
| M4 | Custom compatibility architecture decision | **IN PROGRESS** (report 09) — Option E selected; B/C gated on authorized hw + admission |
| M5 | Type111 control/transport (offline, testable) | **IN PROGRESS** — `frame_gate.py` (bounded generation-gated delivery, 11 tests) |
| M6 | Fail-closed factory integration contracts/adapters | **IN PROGRESS** — `src/claritylink-honda/factory_integration_contract.py` (8 tests) |
| M7 | Synthetic concurrent Type110/Type111 integration tests | **IN PROGRESS** — `tests/integration/test_cl_factory_01_dual_stream_gate.py` (7 scenarios) |
| M8 | Android API17 compatibility regression | not started |
| M9 | Bounded read-only ADB collection plan (for separate approval) | **DRAFTED** (report 11) — inert; awaits owner approval |
| M10 | Feasibility + deployment prerequisites | **IN PROGRESS** (report 10) — evidence-gap matrix |

## Reports
- [01 — Artifact inventory & tool readiness](01-artifact-inventory.md)
- [02 — Deodex pipeline & build analysis](02-build-and-odex-analysis.md)
- [03 — CarPlay receiver architecture](03-carplay-receiver-architecture.md)
- [06 — Navigation → cluster data flow](06-navigation-architecture.md)
- [07 — ExternalDisplay host architecture](07-externaldisplay-architecture.md)
- [08 — Cluster composition & safety](08-cluster-composition-and-safety.md)
- [09 — Compatibility options & decision](09-compatibility-options.md)
- [10 — Remaining evidence gaps](10-remaining-evidence-gaps.md)
- [11 — Read-only ADB collection plan (proposal)](11-adb-collection-plan.md)
- (forthcoming) 04 Type110/Type111; 05 native decoder/video; 12 feasibility.

## Key standing facts (see report 01 for evidence)
- Preserved platform: Honda ADA (Andromeda-class) head unit, Android 4.2.2 / API 17 / armeabi-v7a.
- Factory APKs are **ODEX-separated** (code in `.odex`); manifests/permissions/components are analyzable now, Java
  bodies require a Dalvik-API17 deodex step. Native binaries (`jmcs`, `libcarplay_proxy`) are ARM, unstripped.
- M3: factory cluster Navigation is **structured turn-by-turn data** rendered host-side into Android Views on Display 1; the host composes a **main layer + a preempting interrupt/warning layer** (factory warning precedence exists; its preservation under third-party content is UNPROVEN, U-05).
- Prior CL-SYS-01A: native `jmcs → libcarplay_proxy` screen-stream callback family is **singleton** (no second-screen
  / Type111 evidence at the proxy); receiver→Display-1 edge **UNKNOWN**. This campaign re-verifies against artifacts.

## Cross-references
- Prior factory study: `research/honda/cl-sys-01a-factory-android-architecture.md`.
- HondaHack reports (architectural reference only; no proprietary code reused): private `HondaHack-Research` repo.
- Evidence boundary: `docs/security/public-private-evidence-boundary.md`; safety: `docs/security/vehicle-safety-gates.md`.

## Open Type111 / display-ownership questions (unresolved)
- Can any factory path admit a second screen stream? (native proxy singleton suggests no; APK/framework graph pending)
- Does the cluster consume pixels, Surfaces, or structured nav values? (M3)
- Who owns Android Display 1 and the Navigation presentation? (M3)
- Authentication ownership for a second stream — **assumed NOT available** via the factory session (no bypass).

## Private evidence (not in this repo)
Exact hashes, paths, build fingerprint/model, deodexed/decompiled output, and raw Ghidra/JADX results are retained
in authorized private storage, consistent with the evidence boundary.
