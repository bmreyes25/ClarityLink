# Implementation Plan: Genuine iPhone-origin Type111 on Honda Display 1

**Branch**: `claude/cl-t111-implementation-usb` | **Date**: 2026-10-28 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/001-genuine-type111-display1/spec.md`

## Summary

Deliver, offline and using only technology already in the repository, the evidence discipline, fixture-intake rules, synthetic withdrawal/coexistence proof and staged acceptance gates needed to *eventually* show genuine iPhone-origin Type111 video on Honda Display 1 beside Type110. Every Honda-specific method (Type111 SETUP fields, protection context, Display 1 admission, geometry, page ownership, warning priority, restoration) is `UNK` and stays blocked pending evidence (BLK-02/03/04). Nothing here sets `safeForHonda()` true or touches a car or iPhone.

The plan is deliberately split into a prerequisite evidence/gate review (Phase 1), bounded offline-only CL-T111-INGEST-01 work (Phase 2), and blocking placeholders that are recorded but never attempted (Phase 3). Phase numbers match `tasks.md`. The canonical F1–F13 contract is `docs/roadmap/finish-line-definition.md` and the spec already resolves it (BLK-01 is closed and is not a blocker); the open blockers are BLK-02..06. No F-item is claimed passed and no implementation is claimed done.

## Technical Context

**Language/Version**: Python 3 (host lab receiver `claritylink_jmcs`, `claritylink-honda`, tools); Java for API17/Dalvik lab (`android/`); C for the native ARMv7/API17 build (`native/`). No new language or dependency.

**Primary Dependencies**: existing only — FFmpeg (host decode), pytest (`requirements-test.txt`), Android 4.2.2 API17 emulator toolchain, existing `tools/publish_checkpoint.sh` and `tools/verify_remote_publication.py`.

**Storage**: files in Git (public-safe only); private evidence stays outside Git.

**Testing**: pytest via `tools/run_tests.sh`; API17 emulator runners for lab acceptance; tests must run on the claimed exact SHA (Constitution VIII).

**Target Platform**: macOS host, API17 emulator (lab). Honda target is **not** a platform for this plan.

**Project Type**: existing multi-component research/library repository.

**Performance Goals**: UNK for Honda. F10 limits are not set here; they must be declared by the owner/independent reviewer before any target measurement (blocked placeholder T025). Lab numbers are `SYNTHETIC_TEST_VALUE`.

**Constraints**: offline only; no vehicle, Honda ADB, connected iPhone, authentication bypass, secret extraction, or CAN; fail closed on every unknown.

**Scale/Scope**: one feature. The documentation deliverable consists of `spec.md`, `plan.md`, `checklists/requirements.md`, `tasks.md` and `analysis.md` under this spec directory. Offline code/test work is described in `tasks.md` and has not been performed by this documentation step.

## Constitution Check (pre-design)

Source: `.specify/memory/constitution.md` v1.0.0, which narrows `AGENTS.md`.

| Principle | Gate | Documentation review |
|---|---|---|
| I Evidence before interfaces | Every interface claim cites evidence or is `UNK` | Consistent in the planned scope; unknowns remain explicit |
| II `safeForHonda()` false | No task sets or weakens it | Preserved by FR-018 and the task guard |
| III No vehicle/iPhone ops | Offline only | Phases 1–2 are offline; Phase 3 contains non-executable blockers |
| IV No auth bypass/secrets | Context only from authorized provider | FR-005 requires fail-closed authorized context |
| V Unknown fails closed | Honda adapters remain disabled | FR-006, FR-010 and FR-012 retain unknown boundaries |
| VI Type110 continuity | Regression evidence for shared-path change | FR-013 requires regression evidence |
| VII Genuine never simulated | Provenance + labeling | FR-003 separates genuine provenance from synthetic fixtures |
| VIII Exact SHA | Tests run on claimed SHA | Exact-tree evidence remains a task acceptance requirement |
| IX Public/private | Sanitized only | FR-004 preserves the public/private boundary |
| X Protected publication | Scoped review and publication workflow | Task T032 requires the protected workflow; no exception is requested |

## Project Structure

### Documentation (this feature)

```text
specs/001-genuine-type111-display1/
├── spec.md                      # exists
├── plan.md                      # exists (this file)
├── tasks.md                     # exists (docs-only; tasks not executed)
├── analysis.md                  # exists (consistency and safety findings)
└── checklists/
    └── requirements.md          # exists
```

Not created by this step and not required by `tasks.md`: `research.md`, `data-model.md`, `quickstart.md`, `contracts/*` and `checklists/safety-evidence.md`. Any of them may be added later as its own reviewed unit; nothing below depends on their existence.

### Source Code (repository root) — existing locations, referenced not changed by this run

```text
src/claritylink-jmcs/claritylink_jmcs/   # receiver, media, decoder, security, stream_dispatch, frames
src/claritylink-honda/                   # failsafe_coordinator.py, type111_ingest.py
src/claritylink-renderer/honda_output.py # disabled Honda Display 1 adapter
android/                                 # API17 lab: pane lease, host withdrawal
tests/{jmcs,integration,honda,display}/  # existing regression coverage
docs/architecture/cl-t111-ingest-01-offline-type111-ingest.md
```

**Structure Decision**: No new top-level component. Future implementation tasks add narrowly scoped files beside the existing ones (tests under `tests/integration/`; an intake/provenance check only if a gap is confirmed), each as a separate reviewed development unit with an explicit file scope. This documentation deliverable writes the five feature files listed above.

## Phases

Phases match `tasks.md`. Every task there carries canonical F-IDs from `docs/roadmap/finish-line-definition.md`.

| Phase | Name | Evidence classes produced | Status |
|---|---|---|---|
| 1 | Prerequisite evidence and gate review (T001–T008, Gate G1) | none new (record review) | Must complete first; not yet performed |
| 2 | Offline-only CL-T111-INGEST-01 integration and verification (T009–T020) | SYN, VS | Not started; starts only after Gate G1 is recorded |
| 3 | Blocking requirement and authorization records (T021–T030) | none; documentation of missing evidence only | **BLOCKED — recorded, never attempted** (BLK-02..06) |
| 4 | Public-safe history and traceability maintenance (T031–T033) | VS for scoped review only; no F-item outcome | Not started; follows verification of the relevant unit |

### Phase 1 — Prerequisite evidence and gate review
Record the campaign baseline, re-read the canonical F1–F13 contract and goal precedence, confirm the authorization level (offline only), confirm `safeForHonda()` is `false`, inventory the existing components and tests by evidence class, and baseline the public-safety and source-discovery checks. Output is a recorded gate decision (Gate G1), not code. BLK-01 is resolved; no owner confirmation is needed.

### Phase 2 — CL-T111-INGEST-01 (offline only)
Using only existing components: the host `Receiver` (framing, security provider, decoder, per-stream dispatcher), the content-agnostic decoded-frame / lease bridge (`frames.py`, `type111_ingest.py`), the timer-driven heartbeat/tick, receiver-code fault mapping, and the ordered closers (revoke first, then independent cleanups). Add or confirm tests for the synthetic disconnect matrix and Type110 continuity. Existing code and tests are recorded history (VS); each task re-establishes its claim on the exact SHA and adds regression coverage only for a confirmed gap. All results are labeled SYN/VS and never reported as MGI, HST or MPA.

### Phase 3 — Blocking placeholders
Tasks T021–T030 record the Honda receiver contract (BLK-02), Honda Display 1 contract and warning/page/geometry (BLK-03), the missing genuine iPhone fixture and its provenance requirements (BLK-04), independent safety review (BLK-05), owner authorization (BLK-06), plus dependent performance and rollback gates. They are not executable target work. The only permitted action is to document the missing requirement and fail closed. Unblocking requires supplied, reviewed evidence and a new plan revision. T031–T033 cover scoped public-safe publication and traceability maintenance.

### Phase 4 — Public-safe history and traceability maintenance
Review only the task-owned files, retain all restricted evidence outside public Git, and use the explicit-scope publication workflow for a verified public-safe unit. Do not treat publication as F13 completion unless its canonical merged-history evidence is satisfied. Re-map the F crosswalk if its canonical sources change.

## Post-Design Constitution Check

Re-evaluated against the current `spec.md` and `tasks.md`: all ten principles remain satisfied by the plan as written. No exception to Principles II–V is requested. This is a plan-level check, not a claim that any task has been executed or any F-item passed.

## Complexity Tracking

None.
