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
| M3 | Factory Navigation + Display 1 architecture | not started |
| M4 | Custom compatibility architecture decision | not started |
| M5 | Type111 control/transport (offline, testable) | not started |
| M6 | Fail-closed factory integration contracts/adapters | **IN PROGRESS** — `src/claritylink-honda/factory_integration_contract.py` (8 tests) |
| M7 | Synthetic concurrent Type110/Type111 integration tests | not started |
| M8 | Android API17 compatibility regression | not started |
| M9 | Bounded read-only ADB collection plan (for separate approval) | not started |
| M10 | Feasibility + deployment prerequisites | not started |

## Reports
- [01 — Artifact inventory & tool readiness](01-artifact-inventory.md)
- [02 — Deodex pipeline & build analysis](02-build-and-odex-analysis.md)
- [03 — CarPlay receiver architecture](03-carplay-receiver-architecture.md)
- (forthcoming) 04 Type110/Type111; 05 native decoder/video; 06 navigation;
  07 externaldisplay; 08 cluster/safety; 09 compatibility options; 10 evidence gaps; 11 ADB plan; 12 feasibility.

## Key standing facts (see report 01 for evidence)
- Preserved platform: Honda ADA (Andromeda-class) head unit, Android 4.2.2 / API 17 / armeabi-v7a.
- Factory APKs are **ODEX-separated** (code in `.odex`); manifests/permissions/components are analyzable now, Java
  bodies require a Dalvik-API17 deodex step. Native binaries (`jmcs`, `libcarplay_proxy`) are ARM, unstripped.
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
