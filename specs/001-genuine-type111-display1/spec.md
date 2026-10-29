# Feature Specification: Genuine iPhone-origin Type111 secondary CarPlay on Honda Display 1

**Feature Branch**: `claude/cl-t111-implementation-usb` (existing; no feature branch created by this spec)

**Created**: 2026-10-28

**Status**: Draft — evidence-gated, offline-only. `safeForHonda()` remains `false`. `VEHICLE_DEPLOYMENT_NOT_AUTHORIZED`.

**Input**: User description: "Genuine iPhone-origin Type111 secondary CarPlay video to Honda Display 1 while Type110 remains active on the center display (evidence-gated, offline-only, safeForHonda() remains false)."

## Scope statement

This spec defines what must be **true and proven** before genuine secondary CarPlay video from an iPhone can be shown on factory Display 1 while normal Type110 CarPlay continues on the center display (Display 0). It specifies outcomes, evidence gates and the offline work that may proceed now. It does **not** specify, and must not be read as authorizing or inventing, any Honda protocol field, authentication detail, OEM display method or vehicle procedure.

Nothing here authorizes a car, Honda ADB, a connected iPhone, installation, firmware/service change or any vehicle test (AGENTS.md; `docs/safety/vehicle-testing.md` Levels C and D). The canonical goal sentence is in `docs/project/primary-goal.md`. Navigation UIs, map renderers, mirrored Display 0, replayed video and the NAV-LAB track are explicitly **not** this feature and are never substitutes.

## Evidence classes used throughout

Every claim in this spec and its companions carries exactly one of these classes. They are never interchangeable, and a gate is never satisfied by a weaker class.

| Code | Class | Meaning |
|---|---|---|
| VS | Verified software | Offline code/tests that the repository records as passing (e.g. CI on the merged SHA). This spec did not re-run them; any "tested" claim for a new unit must be re-established on its exact SHA (Constitution VIII). |
| SYN | Synthetic behavior | Models, hand-built or locally generated fixtures, API17 emulator lab. Exercises logic only. Never Honda or iPhone evidence. |
| HST | Honda static evidence | Statically identified in preserved Honda artifacts (decompilation/disassembly). Says what code appears to do; not runtime behavior, not OEM permission. |
| UNK | Unknown interface | No established contract or evidence. Recorded as unknown; fails closed. Never filled by assumption. |
| MGI | Missing genuine iPhone-origin evidence | Frames/bytes that actually came from a real iPhone's Type111 stream and passed through ClarityLink code. None exist. |
| MPA | Missing physical acceptance | Pixels on the real cluster/Display 1 with page ownership and warning priority respected. None exist. |

The third-party 43P PlayPort observation (`OBSERVED-3P` in repo vocabulary) is prior art. It is not MGI, not HST, not MPA.

### Crosswalk to the canonical evidence categories

`docs/project/primary-goal.md` defines five canonical categories, which are never interchangeable. The classes above are finer-grained and map onto them as follows. Reports must name the canonical category.

| This spec | Canonical category (primary-goal.md) |
|---|---|
| SYN, VS (lifecycle code) | Synthetic lifecycle |
| SYN, VS (framing/decoder), HST (Type110 only) | Type111 protocol handling |
| MGI | iPhone-origin video (third-party `OBSERVED-3P` is not this) |
| HST, UNK (receiver) | Honda receiver integration |
| MPA, HST (display ownership), UNK (display) | Physical Display 1 output |

The canonical matrix marks all ten pipeline stages **UNVERIFIED end to end**; the Honda and Physical columns may not use `LAB` or `OBSERVED-3P`.

## Blocking requirements (open items: BLK-02..06)

- **Canonical F1–F13 source (not a blocker).** The F1–F13 contract is `docs/roadmap/finish-line-definition.md`; goal precedence is `docs/project/primary-goal.md`. This spec defines no F-criteria of its own and maps to those rows (see Traceability). The canonical conclusion is **NOT PASSED** ("Current conclusion" in the finish-line document); no F-item is claimed passed here.
- **BLK-02 — Honda Type111 receiver contract (UNK).** No supported Honda capability advertisement, SETUP schema, session ownership, protection context, data-port ownership, revocation or teardown contract exists in reviewed evidence (`RECEIVER_AUTHORIZED_SPEC_REQUIRED`).
- **BLK-03 — Honda Display 1 admission contract (UNK).** No supported frame/View admission method, owner/loss notification, Navigation eligibility, safe-area geometry, warning precedence or restoration procedure exists (`DISPLAY_SUPPORTED_PATH_NOT_FOUND`).
- **BLK-04 — Genuine iPhone-origin Type111 bytes (MGI).** No real iPhone byte stream has passed through ClarityLink code. Obtaining sanitized fixtures needs separate explicit owner authorization and a legitimately authenticated session (CL-REC-01); it cannot be done under the current offline authorization.
- **BLK-05 — Independent vehicle-safety review (not recorded).** Required before any target-facing work.
- **BLK-06 — Level C owner authorization (not present).** Required separately for any bench-with-phone, live-iPhone, or vehicle activity.

## What exists today, by evidence class

| Area | VS | SYN | HST | UNK | MGI / MPA |
|---|---|---|---|---|---|
| Genuine receiver/session context | Fail-closed auth/handoff interfaces in `claritylink_jmcs` | Synthetic/replay authority; lab `/info`+SETUP | Honda `jmcs` has internal iAP2/MFi/AirPlay session ownership with no external handoff found (R6C/R6D) | Authenticated-session handoff for a ClarityLink receiver on Honda; legitimate security-context source | MGI: no real authenticated session handled by ClarityLink |
| Protected Type111 transport/decode | Framing, avcC/Annex-B, FFmpeg decode, bounded per-stream dispatcher (`media.py`, `decoder.py`, `stream_dispatch.py`) | Hand-built/generated lab fixtures; clear/injected lab key | Honda Type110 framing/KDF; Honda skips Type111 SETUP | Whether Type111 reuses Honda framing/KDF; Type111 `streamConnectionID`, key derivation, timing | MGI: third-party PlayPort saw frames; ClarityLink never processed real bytes |
| Display 1 admission/withdrawal | Lease fence, coordinator, host-owned autonomous withdrawal (CL-INT-03/04, CL-INGEST-HARDEN); `HondaDisplay1OutputAdapter` fails closed | `SimulatedClusterHost`, API17 pane lease | ExternalDisplay AP Binder control/status found; no arbitrary-frame admission method | Every Honda admission/withdrawal/restore method | MPA: no pixels on a real Display 1 |
| Type110 coexistence | API17 lab Type110 continuity | Synthetic dual-stream (R7A/R7D lab) | Honda Type110 path recovered statically | Behavior under a real second stream on Honda | MPA: none |
| Warning precedence/restoration | Lab warning preemption (CL-R1/R4/R7) | Modeled interrupt/lease withdrawal | — | Honda warning priority, z-order, page ownership | MPA: none; unsafe warnings are never deliberately induced |
| Provenance | Evidence ledger; public-safety CI gate | Frame/label conventions | Hash-pinned preserved Honda artifacts (private) | — | — |

## User Scenarios & Testing *(mandatory)*

The "user" is the project owner/engineer (and later an independent safety reviewer) who must be able to decide, with evidence, whether each pipeline stage is real. Stories are ordered so each is independently useful and none claims Honda compatibility from offline results.

### User Story 1 - Evidence ledger that cannot overstate (Priority: P1)

**Finish-line items**: F13 (public-safe history and private evidence inventory); reporting discipline for F1–F12.

An engineer opens one traceable record of each pipeline stage (receiver/session, protected transport, decode, Display 1 admission, withdrawal, Type110 coexistence, warnings, restoration, provenance) and sees per stage its evidence class, the artifact/SHA behind it, and what is still missing.

**Why this priority**: The dominant risk is misreporting synthetic success as Honda or iPhone evidence. A trustworthy ledger gates every later decision.

**Independent Test**: Cross-check every ledger row against its cited sources; any row whose claim exceeds its class (e.g. SYN reported as MGI or MPA) fails.

**Acceptance Scenarios**:

1. **Given** the existing synthetic ingest and lease-fence tests, **When** the ledger is read, **Then** they appear as SYN/VS only, with MGI and MPA shown as missing.
2. **Given** the 43P PlayPort observation, **When** the ledger is read, **Then** it appears as third-party prior art and not as MGI/HST/MPA.
3. **Given** the ledger references finish-line items, **When** it is read, **Then** each reference uses the canonical F1–F13 IDs from `docs/roadmap/finish-line-definition.md` and none is marked PASS.

---

### User Story 2 - Genuine receiver/session context and protected Type111 ingest, proven offline against sanitized fixtures (Priority: P2)

**Finish-line items**: F1 (one authenticated session, independent stream identity), F3 (genuine Type111 accepted, configured, delivered), F4 (stream-specific lifecycle and stale-generation rejection). Offline fixtures can never alone satisfy F1/F3 ("lab fixtures do not count").

Once sanitized genuine iPhone-origin Type111 fixtures exist (BLK-04), the engineer replays them offline through the same receive → unprotect → config → decode path used for synthetic content and confirms real-byte handling, with failures failing closed and Type110 state untouched.

**Why this priority**: This is the true critical path to "genuine", but it is blocked on BLK-04 (and BLK-02 for the Honda receiver). Until then only fixture-agnostic readiness (provenance schema, redaction rules, replay acceptance rules) can proceed.

**Independent Test**: Submit fixtures with and without provenance; the intake accepts only fixtures whose provenance and redaction checks pass and rejects synthetic content labeled genuine.

**Acceptance Scenarios**:

1. **Given** a fixture with no provenance record or a synthetic label, **When** submitted as "genuine iPhone-origin", **Then** it is rejected and MGI is reported missing.
2. **Given** a malformed, truncated or wrong-generation frame, **When** replayed, **Then** the Type111 path closes only its own resources and Type110 state is unchanged.
3. **Given** the protection context is absent or unverifiable, **When** ingest starts, **Then** it fails closed with no frames reaching any sink.

---

### User Story 3 - Display 1 admission and withdrawal gated by a reviewed contract (Priority: P3)

**Finish-line items**: F5 (permitted, reviewed frame-sink boundary), F6 (Navigation-page selection and physical geometry), F8 (disconnect/failure leaves no stale content), F9 (reliable host-owned restoration). Synthetic withdrawal is SYN and does not satisfy F5, F6, F8 or F9 on the target.

The engineer can show that the Honda Display 1 adapter stays disabled and fail-closed until a documented, reviewed admission contract exists, and that host-owned withdrawal (lease expiry, producer death, disconnect) is complete on the synthetic host so it is ready to bind to that contract later.

**Why this priority**: Synthetic withdrawal is real, buildable offline value; the Honda binding is UNK and must not be guessed.

**Independent Test**: Run the disconnect/failure matrix on the synthetic host and confirm zero residual project-owned frames/views/sessions within a declared bound; confirm the Honda adapter cannot be enabled by caller-supplied metadata.

**Acceptance Scenarios**:

1. **Given** an active synthetic lease, **When** the producer dies, the lease expires, or the stream disconnects, **Then** Display 1 returns to the factory baseline (synthetic) within the declared bound.
2. **Given** no reviewed Honda admission contract, **When** any caller requests Honda admission, **Then** it fails closed with `EVIDENCE_REQUIRED_HONDA_DISPLAY_ADMISSION_API`.

---

### User Story 4 - Type110 coexistence and warning precedence as measurable gates (Priority: P4)

**Finish-line items**: F2 (Type110 center-display UI, touch, audio, navigation unaffected), F7 (factory instruments and warnings retain priority).

The engineer can read, per gate, the observable signals, baseline, bounds and stop conditions for proving Type110 (display, touch, audio, calls) is unaffected by a Type111 stream and that factory warnings keep priority and restore afterward — without any step inducing a real warning or touching a vehicle.

**Why this priority**: These are the safety-critical gates. They can be fully *specified* offline but only *proven* on a bench/vehicle under BLK-05/06.

**Independent Test**: Review that every gate names its signal, baseline, bound, required evidence class and required authorization; no gate is satisfiable by SYN evidence alone.

**Acceptance Scenarios**:

1. **Given** the Type110 continuity gate, **When** only API17 lab evidence is offered, **Then** the gate stays open and is labeled SYN.
2. **Given** the warning-precedence gate, **When** reviewed, **Then** it forbids deliberately inducing unsafe warnings and requires a reviewed priority contract.

---

### User Story 5 - Staged bench and first-vehicle evidence gates (Priority: P5)

**Finish-line items**: F10 (predeclared performance and resource gates), F11 (independent vehicle-safety review), F12 (reproducible rollback and verification); the ladder also carries the target evidence for F1–F9.

The owner and an independent reviewer have a staged ladder — offline replay, authorized bench receiver with phone (no Honda), parked read-only Honda observation, first parked vehicle display — where each stage lists prerequisites, authorization, stop conditions, rollback and evidence class, and no stage can start before the prior one is accepted.

**Why this priority**: Defines the end state without enabling it; every stage past the first needs Level C authorization.

**Independent Test**: Verify each stage names its authorization and refuses to proceed with missing prerequisites; verify no stage is marked started.

**Acceptance Scenarios**:

1. **Given** the ladder, **When** BLK-05 or BLK-06 is unresolved, **Then** stages 2–4 remain "NOT AUTHORIZED".
2. **Given** a stage-4 proposal, **When** reviewed, **Then** it requires a recorded independent safety review and a rollback demonstrated on non-vehicle equipment.

### Edge Cases

- A fixture labeled genuine whose bytes are synthetic or replayed prerecorded video (rejected; Constitution VII).
- Type111 SETUP accepted by a third-party receiver but not by Honda: third-party success is never carried over.
- iPhone sends Type110 and Type111 in either order, or only Type110 (Type111 optional; Type110 unaffected).
- Type111 stream ends, restarts, or sends a stale generation while Type110 stays active.
- iPhone disconnect, USB drop, receiver crash, decoder death, display-host restart, power cycle, or incomplete initialization: all must reach factory-only state.
- Factory Navigation page not selected: Display 1 content must not appear (UNK: page-ownership signal).
- Factory warning mid-stream: warning wins; content withdrawn or hidden without masking instruments; fresh-frame restoration only after clear.
- Frames with unexpected size/geometry: rejected, not scaled to guessed Honda geometry (geometry is UNK).
- Host process dies while content is visible: autonomous host-owned withdrawal, no dependence on the dead producer.
- Missing or unobservable evidence is a failure or unresolved result, never a pass.

## Requirements *(mandatory)*

### Functional Requirements

**Governance and provenance**

- **FR-001**: The feature MUST classify every claim, test and report by exactly one evidence class (VS, SYN, HST, UNK, MGI, MPA) and MUST NOT report a bare "PASS" or "works". Maps to: F1–F13 (reporting discipline; F13 ledger).
- **FR-002**: The feature MUST reference finish-line items only by the canonical F1–F13 IDs and wording of `docs/roadmap/finish-line-definition.md` (goal precedence: `docs/project/primary-goal.md`), MUST NOT define divergent F-criteria, and MUST NOT mark any F-item PASS from offline, synthetic, third-party or static evidence. Maps to: all of F1–F13 (governance). If the canonical documents change, the traceability table MUST be re-mapped in the same change.
- **FR-003**: Every fixture offered as genuine iPhone-origin MUST carry a provenance record (source device class, authorization reference, capture date, redaction review, hash). Fixtures lacking one, or labeled synthetic, MUST be rejected as genuine. Maps to: F3 (lab fixtures do not count), F13.
- **FR-004**: No private Honda evidence, firmware, captures, credentials, signing material or identifiers MAY enter public Git; only reviewed, sanitized summaries. Maps to: F13.

**Genuine receiver/session context**

- **FR-005**: The receiver MUST obtain any authenticated session and protection context only from a legitimately authorized provider; it MUST NOT bypass, extract or disclose authentication secrets, and MUST fail closed when the context is absent or unverifiable. Maps to: F1.
- **FR-006**: Type111 session ownership, advertisement, SETUP acceptance, data-port ownership, revocation and teardown for Honda MUST remain UNK and fail closed until a contract (BLK-02) is supplied and reviewed; no field, identifier or port MAY be defaulted from prior art. Maps to: F1, F3.

**Protected Type111 transport and decode**

- **FR-007**: The Type111 path MUST receive, unprotect, configure and decode only frames bound to the active session, stream identity and generation, rejecting stale, malformed or unprotected input without affecting Type110. Maps to: F3, F4.
- **FR-008**: Type111 framing, security and timing MUST be treated as hypotheses (prior art / lab profile) until validated by genuine iPhone-origin fixtures (BLK-04); results from generated content MUST be labeled SYN. Maps to: F3.
- **FR-009**: Decoded frames MUST reach the display boundary through a single canonical frame contract; the sink MUST be content-agnostic. Maps to: F3, F5.

**Display 1 admission and withdrawal**

- **FR-010**: The Honda Display 1 output MUST remain disabled and fail closed until a documented admission contract (BLK-03) is reviewed; caller-supplied metadata MUST NOT enable it. Maps to: F5.
- **FR-011**: Display ownership MUST be lease-based and host-owned: content is shown only under a current lease and withdrawn on revoke, expiry, producer death, disconnect or fault, with withdrawal not dependent on the producer. Maps to: F5, F8, F9.
- **FR-012**: On any unexpected state or exception behavior MUST revert to factory-only (`CARPLAY_DISCONNECTED => FACTORY_BEHAVIOR_ONLY` is a target needing evidence, not a demonstrated property). Maps to: F8, F9.

**Type110 coexistence**

- **FR-013**: Any change touching Type111 or shared paths MUST ship regression evidence that Type110 display, touch, audio and navigation behavior is unchanged; Type111 failures MUST close only Type111-owned resources. Maps to: F2, F4.
- **FR-014**: Type110 continuity claims MUST be labeled SYN until measured on an authorized target (MPA). Maps to: F2.

**Warning precedence and restoration**

- **FR-015**: Factory warnings and instruments MUST retain priority; the feature MUST NOT suppress, intercept or mask them, and MUST NOT deliberately induce unsafe warnings. Maps to: F7.
- **FR-016**: Restoration after warning, disconnect or withdrawal MUST be verifiable against a recorded baseline with zero residual project-owned frames/views/sessions within a declared bound; unobservable restoration MUST be treated as failure. Maps to: F8, F9.

**Bench and first-vehicle gates**

- **FR-017**: Each stage beyond offline replay MUST state its exact question, prerequisites, actions, expected results, time/output limits, stop conditions, evidence handling and recovery path, and MUST require separate explicit owner authorization and a recorded independent safety review. Maps to: F1–F9 (target evidence), F11, F12.
- **FR-018**: The feature MUST NOT set `safeForHonda()` true, represent offline permission as vehicle permission, or cause publication/CI to contact a car. Maps to: F1–F13 (non-claim guard: no PASS, no vehicle permission).

- **FR-019**: Rendering MUST respect Navigation-page selection and physical geometry: content appears only while the factory Navigation page is selected and only inside a verified physical safe area with a verified transform. Page-ownership signal, safe area and transform are UNK for Honda and MUST NOT be guessed; frames of unexpected size are rejected, not scaled to guessed geometry. Lab numbers are `SYNTHETIC_TEST_VALUE`. Maps to: F6.
- **FR-020**: Performance and resource limits (frame rate, latency, drops, CPU/memory, queue depth, thermal, soak) MUST be declared before measurement by the owner/independent reviewer and measured on the target path. Lab measurements are SYN and MUST NOT be reported against F10. This spec sets no numeric limits. Maps to: F10.
- **FR-021**: Rollback and verification MUST be a versioned procedure with preconditions, bounded recovery steps and a recovery mechanism independent of the modified component; a modeled rollback is not restoration evidence and a backup alone is not recoverability (`docs/safety/vehicle-testing.md`, Reversibility contract). Maps to: F12 (and F9).

### Key Entities

- **Evidence record**: one claim with evidence class, source artifact/SHA, scope, and missing proof.
- **Genuine-fixture provenance record**: origin class, authorization reference, capture date, redaction review, hash, labeling.
- **Session context**: the legitimately authenticated session and protection context a stream is bound to (contents never recorded).
- **Stream generation**: ownership token fencing Type111 resources from stale input and from Type110.
- **Display 1 lease**: host-owned, expiring right to show content; revocable independently of the producer.
- **Acceptance gate**: named condition with signal, baseline, bound, required evidence class and required authorization.
- **Blocker**: an unresolved external requirement (BLK-xx) with closing evidence.

## Success Criteria *(mandatory)*

These are actionable and verifiable. **No simulated or synthetic result establishes Honda compatibility.** SC-001–SC-006 are offline outcomes only; SC-007 states what offline work cannot achieve.

### Measurable Outcomes

- **SC-001**: 100% of rows in the feature evidence ledger carry exactly one evidence class and a cited artifact; a cross-check finds 0 rows whose claimed result exceeds its class. Maps to: F13 (ledger), F1–F12 (reporting).
- **SC-002** *(F1–F13, governance)*: 100% of user stories, FRs, SCs and plan tasks carry at least one canonical F-ID from `docs/roadmap/finish-line-definition.md`, every F1–F13 is covered by at least one FR and one task, 0 invented F-criteria exist, and 0 F-items are marked PASS.
- **SC-003**: The genuine-fixture intake check rejects 100% of fixtures lacking provenance or labeled synthetic when submitted as genuine, in an offline run on the claimed SHA. Maps to: F3, F13.
- **SC-004**: Across the synthetic disconnect/failure matrix (USB drop, iPhone disconnect, Type111 termination, auth failure, receiver crash, decoder crash, display-host restart, startup without iPhone, repeated cycles), 100% of cases reach factory-only state with zero residual project-owned frames/views/sessions within a declared bound; results are labeled SYN. Maps to: F4, F8, F9.
- **SC-005**: The Honda Display 1 adapter rejects 100% of enablement attempts without a reviewed contract, verified by test on the claimed SHA. Maps to: F5.
- **SC-006**: Every acceptance gate in the bench/first-vehicle ladder names its signal, baseline, bound, required evidence class and required authorization; 0 gates are satisfiable by SYN evidence alone. Maps to: F1–F9 (gate definitions), F10, F11, F12.
- **SC-007** *(not achievable offline — tracked, not claimed)*: MGI (real iPhone-origin frames through ClarityLink code), Honda receiver acceptance, and MPA (pixels on real Display 1 with warning priority) remain **open**. None may be reported satisfied by SC-001–SC-006. Maps to: F1, F3, F4, F5, F6, F7, F8, F9 (open; not claimable offline).

## Assumptions

- The offline authorization (Level A/B) in `docs/safety/vehicle-testing.md` and PR #91 stays in force; Level C/D are not granted.
- Existing merged components (lease fence, coordinator, ingest, host-owned withdrawal, receiver pipeline) are reused; no new technology is introduced.
- Repository claims of passing tests are recorded history, not re-run by this spec.
- `docs/roadmap/finish-line-definition.md` is the canonical F1–F13 contract and `docs/project/primary-goal.md` governs goal precedence. `primary-goal.md` PR statuses (#91, #92 unmerged) are dated 2026-10-23; `git log` now shows both merged, so offline authorization follows #91 as merged. Those documents are not edited by this feature.
- Display 1 geometry, page ownership, warning priority and restoration are UNK; any lab numbers are `SYNTHETIC_TEST_VALUE`.
- A legitimately authenticated bench session, if later authorized, is arranged by the owner; this feature acquires no hardware or secrets.

## Traceability to canonical F1–F13

Source of truth: `docs/roadmap/finish-line-definition.md` (goal precedence: `docs/project/primary-goal.md`). F-names below are short labels for the canonical rows; the canonical wording and evidence requirements govern. **Every F-item is NOT PASSED**; this table maps coverage, not satisfaction. "Offline can show" is limited to SYN/VS/specification and never satisfies the F-item.

| F | Label | User stories | FR | SC | Tasks (tasks.md) | Blocked by | Offline can show |
|---|---|---|---|---|---|---|---|
| F1 | Legitimacy / session | US2, US5 | FR-005, FR-006, FR-017 | SC-006, SC-007 | T012, T015, T026 | BLK-02, BLK-04, BLK-06 | Fail-closed on absent context (SYN) |
| F2 | Type110 | US4, US5 | FR-013, FR-014 | SC-006 | T022, T024, T026 | BLK-06 (target) | Lab continuity (SYN) |
| F3 | Genuine stream | US2 | FR-003, FR-006, FR-007, FR-008, FR-009 | SC-003, SC-007 | T010, T013, T014, T030 | BLK-02, BLK-04 | Intake rejection rules (SYN) |
| F4 | Lifecycle | US2 | FR-007, FR-013 | SC-004, SC-007 | T011, T015, T024 | BLK-04 (genuine) | Stale-generation rejection (SYN) |
| F5 | Sink | US3 | FR-009, FR-010, FR-011 | SC-005, SC-007 | T017, T019 | BLK-03 | Honda adapter fails closed (VS/SYN) |
| F6 | Geometry / page | US3 | FR-019 | SC-006, SC-007 | T018, T021 | BLK-03 | Reject unexpected sizes (SYN) |
| F7 | Warning | US4 | FR-015 | SC-006, SC-007 | T023 | BLK-03, BLK-05 | Gate spec only |
| F8 | Failures | US3 | FR-011, FR-012, FR-016 | SC-004, SC-007 | T016, T024 | BLK-03 (target) | Synthetic matrix (SYN) |
| F9 | Restoration | US3, US5 | FR-011, FR-012, FR-016, FR-021 | SC-004, SC-007 | T016, T020, T024 | BLK-03, BLK-06 | Synthetic withdrawal (SYN) |
| F10 | Performance | US5 | FR-020 | SC-006 | T025 | BLK-05, BLK-06 | Gate declaration only |
| F11 | Independent safety | US5 | FR-017 | SC-006 | T028, T029 | BLK-05 | Review-packet requirements only; AI review is not approval |
| F12 | Rollback | US5 | FR-017, FR-021 | SC-006 | T027 | BLK-06 | Procedure spec only |
| F13 | Public-safe history | US1 | FR-001, FR-002, FR-003, FR-004 | SC-001, SC-002, SC-003 | T001–T010, T013–T014, T020, T030–T033 | — (publication needs the protected workflow) | Ledger and scans (VS) |

Governance-only items (FR-001, FR-002, FR-018, SC-002) apply to all of F1–F13 and are not counted as coverage of any single F-item. If the canonical documents change, re-map this table in the same change (T033).
