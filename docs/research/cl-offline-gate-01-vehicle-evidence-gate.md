# CL-OFFLINE-GATE-01 — Offline-first Type111 vehicle evidence gate

**Scope:** offline research only. No vehicle, Honda ADB, live iPhone, APK installation, Binder call, display injection, firmware or CAN activity occurred. `safeForHonda()` remains `false`; `RECEIVER_AUTHORIZED_SPEC_REQUIRED` and `DISPLAY_SUPPORTED_PATH_NOT_FOUND` are unchanged. This document authorizes no vehicle session.

**Base:** `origin/main` `51fa9b14278835c21787e5d13c8df0ab97c930f6` (PR #89 merged). PR #87 and PR #88 were open at the time of writing and are not modified by this record.

## Decision

**`CAR_SESSION_NOT_JUSTIFIED_SPEC_REQUIRED`.**

After exhausting the preserved offline evidence, none of the 19 tracked questions is `CAR_EVIDENCE_REQUIRED`. Every question that gates the next Type111 integration step is `AUTHORIZED_SPEC_REQUIRED`: a vendor or integrator statement, not another observation, is what is missing. The remaining car-observable items either cannot change any gate, concern only the unsupported private rendering route, or are already established from existing evidence.

The CL-OBS-02 camera-only observation is **superseded as the next vehicle test**. It is neither a completed nor a failed vehicle session. PR #89's documents and the evidence tool are preserved unchanged; this record does not edit them.

## What this campaign adds to earlier findings

| # | New finding | Class | Effect |
|---|---|---|---|
| N1 | The host's decoded layout resources define explicit Display 1 regions: a base meter region of about 580×270 px at the Display 1 origin and a factory Navigation view set spanning about x 60–524, y 0–215 (compass graphics start near y 0; text and route views start near y 23). The saved factory Navigation screenshot matches these layouts. | `HONDA_STATIC_CONFIRMED` + `OBSERVED_IN_SAVED_EVIDENCE` | Closes the "no OEM rectangle found" statement, which examined compiled code but not decoded resources. |
| N2 | Two camera/frame pairs from different poses fit an isotropic, unrotated, unmirrored mapping from Display 1 to the physical cluster (fit error of a few photo px). Content at y 24–215 is fully visible; Display 1 content is truncated at the left and right edges, by native overlay graphics or a panel boundary, to about x 62–75 at the top rows (35–48 in lower rows) to about x 523–548 in the observed casting state. | `INFERRED` (state-specific, ±15 px) | Replaces "physical aperture unknown" with a bounded estimate. Not an OEM SafeArea. |
| N3 | The hash-verified receiver binary and its proxy library contain none of the current AirPlay secondary-display vocabulary (alt-screen, view areas, corner masks, UI context and related feature names). | `HONDA_STATIC_CONFIRMED` (absence of strings) | Supports "the stock unit does not offer Type111" and shows no configuration route exists. |
| N4 | The host's code is written to log page and status records at INFO under the host service's tag. The logger is observed emitting in saved captures, but no page/status record was observed there. The host's main-layer child count is higher by one in the casting state than in every other saved state. | `OBSERVED_IN_SAVED_EVIDENCE` + static | Corrects "no attributable log record exists"; consistent with the casting view being one additional child of the host layer. |
| N5 | No Bitmap, Surface, file-descriptor or shared-memory parameter exists in the reviewed host Binder interfaces; the renderer service is not bindable. Re-verified against decoded interfaces, not only prior reports. | `HONDA_STATIC_CONFIRMED` (negative, bounded) | Independent confirmation of Q02. |
| N6 | Owner-reported runtime observations are incorporated as `OWNER_REPORTED_RUNTIME_OBSERVATION`: existing casting disappears when leaving Navigation, returns on re-entry, and Stop Casting restores the factory Navigation appearance. | owner report | Removes the rationale for a camera-only session. Not an OEM contract and not an integrity-verified recording. |

## A. Offline evidence inventory

Raw items stay in private storage; this table records classes and availability only.

| Class | Status | Notes |
|---|---|---|
| Factory Navigation APK, decoded host resources, deodexed host services and libraries | Found | Decoded layouts and styles were not previously cited by the geometry reports. |
| Receiver binaries (hash-verified) and proxy library | Found | Hashes match the values recorded in earlier reports. |
| Display 1 screenshots: factory Navigation, HondaHack Advanced Meter, HondaHack Screen Casting (800×480) | Found | Identity recorded in the private manifest; several copies are byte-identical. |
| Physical cluster photographs (factory Navigation, casting Maps/Music, home pages) | Found | Used for N2. Personal photo library was not searched. |
| SurfaceFlinger, WindowManager and display dumps (Sept 25 and Sept 28 states) | Found | Factory and casting states are structurally identical on Display 1 apart from N4. |
| Saved host logs for eight cluster/CarPlay states | Found | Source of N4. |
| 43P current-iOS lab session, 43T0 reports, iAP2 and Type110/111 research | Found (public) | Third-party lab evidence stays separate from Honda evidence. |
| Original Door Open (Test 4C) footage | Not located | Also noted by CL-R10B; only summaries exist. Owner action (Q17). |
| Private archive backup/recovery verification | Unverified | Outside this campaign. |

## B. Navigation geometry report

All bounds are in Display 1 pixels unless stated.

| Candidate rectangle | Bounds | Evidence | Class | Applies to | Remaining uncertainty |
|---|---|---|---|---|---|
| Android logical Display 1 | (0,0)–(800,480) | Display service and compositor dumps | `OBSERVED_IN_SAVED_EVIDENCE` | Android output canvas | None. Not the physical aperture. |
| Host base meter region | about (0,0)–(580,270) | Decoded host layout and style | `HONDA_STATIC_CONFIRMED`; layout variant runtime-inferred | Factory-host content | Other models use different regions. |
| Factory Navigation view set | about x 60–524, y 0–215 (text/route views from about y 23) | Decoded layouts; matches the saved Display 1 screenshot | `HONDA_STATIC_CONFIRMED` + observed | Factory Navigation page content | Union of views, not a declared SafeArea. |
| HondaHack layout root and cast region | root 584×215; cast (0,24)–(584,215) | Third-party decoded layout; observed at the same coordinates in saved Display 1 frames | observed | HondaHack only | Layout-local until N2. |
| Physically visible cast content (casting state) | about x 62–75 (top rows) / 35–48 (lower rows) → 523–548; all of y 24–215 | Two photo/frame pairs, similarity fit | `INFERRED` | One state | ±15 px; other states unobserved (Q07). |
| OEM CarPlay SafeArea / view areas | Not established | None in preserved set | `UNKNOWN` | CarPlay receiver contract | Needs Q06. |

Interpretation: Display 1 maps 1:1 and without rotation onto the cluster in the observed region, but its content is truncated at the left and right edges, by native overlay graphics (clearly so at the left) or a panel boundary. The factory Navigation view set and HondaHack's own 50 px side padding both fit inside the visible range. A 584-px-wide cast overruns it by roughly 100 px in total. The data do not show whether the overlay is a compositor layer or a mask. Dimensions describe the factory host and one observed state; they do not define what a CarPlay receiver should advertise.

## C. Type111 admission gap report

Proven or well supported: stock SETUP skips Type111 and writes no response; Type110 uses the legacy AES-CTR path; the display descriptor builder yields a single main-screen entry; the receiver's platform delegates are compile-time and OEM-internal with no plugin loader or display setting (CL-IF-02A); N3. External projects show that a stock-first interposition design works on other vehicles with a comparable receiver library generation, hash-gated per firmware. A third-party lab session (43P) shows a current iPhone requesting view-area and corner-mask features and exercising Type111; it is not Honda evidence.

Not established: the accepted second-display descriptor and feature schema, the SETUP request/response shape, key-derivation inputs and protection profile for Honda, independent listener ownership, revocation and teardown, and Type110 continuity under an added advertisement.

The barrier between protocol evidence and an authorized path is authorization: the only places a supported seam could exist are the integrator's own licensed SDK integration and Honda's firmware, neither of which the repository holds. A passive trace cannot cross it, because the stock session never contains a Type111 exchange. Successfully observing Type111 packets elsewhere does not prove the Honda can admit a second stream.

## D. Display 1 admission gap report

Established: the host owns all Display 1 windows (full-frame bottom, main and interrupt roots); the interrupt root is attached last; the page the cluster shows follows a status record from the cluster-controller side, with a waiting/displaying handshake; the factory Navigation views are created in-process; the only demonstrated third-party path is private in-process view insertion (N4, N5). Technical reachability of exported services or generic Android display APIs is not authorization.

Not established, and not resolvable from the car: caller authorization, accepted frame type, geometry contract, page ownership and revocation, warning precedence across classes, stale-frame withdrawal, behavior on host or display loss, and factory restoration guarantees. A vehicle measurement cannot supply a guarantee that only the host/controller owner can make.

## E. Car evidence-gap matrix

Categories: `ALREADY_ESTABLISHED`, `OFFLINE_RESOLVABLE`, `CAR_EVIDENCE_REQUIRED`, `AUTHORIZED_SPEC_REQUIRED`, `NOT_JUSTIFIED`, `UNKNOWN`. There are no `CAR_EVIDENCE_REQUIRED` rows.

| ID | Question | Category | Priority | Verdict |
|---|---|---|---|---|
| Q01 | Supported receiver extension for an additional CarPlay display stream | `AUTHORIZED_SPEC_REQUIRED` | P0 | Spec inquiry: owner decision. Car: NO-GO. |
| Q02 | Supported Display 1 frame-admission contract | `AUTHORIZED_SPEC_REQUIRED` | P0 | Spec inquiry: owner decision. Car: NO-GO. |
| Q03 | Does the stock receiver advertise a second display or alt-screen capability? | `OFFLINE_RESOLVABLE` | P4 | NO-GO: cannot change any gate; a positive result would contradict high-confidence static evidence. |
| Q04 | Factory host content region and Navigation content bounds in Display 1 coordinates | `ALREADY_ESTABLISHED` | P2 (record) | Closed. Corrects earlier 'no OEM rectangle found' statements, which examined only compiled code, not decoded resources. |
| Q05 | Physically visible region of Display 1 content (observed state) | `OFFLINE_RESOLVABLE` | P3 | Offline estimate adopted. Further car data: NO-GO. |
| Q06 | Authoritative CarPlay SafeArea (view areas) for the Honda cluster | `AUTHORIZED_SPEC_REQUIRED` | P1 | Spec inquiry. Car: NO-GO. |
| Q07 | Variation of native overlay occlusion across cluster states | `UNKNOWN` | P3 | NO-GO until Q01/Q06 outcome is known. |
| Q08 | Existing casting follows Navigation page; Stop Casting restores factory Navigation | `ALREADY_ESTABLISHED` | P4 | Closed (owner report plus static evidence). Repeating the camera-only observation is NOT_JUSTIFIED. |
| Q09 | Does the host detach an injected child on page change or stop? | `NOT_JUSTIFIED` | P4 | NO-GO: concerns only the unsupported route. |
| Q10 | Warning/interrupt precedence and withdrawal for third-party content | `AUTHORIZED_SPEC_REQUIRED` | P1 | Spec. Car: NO-GO. |
| Q11 | Honda Type111 SETUP schema, key derivation, protection profile, VideoConfig | `AUTHORIZED_SPEC_REQUIRED` | P0 | Spec. Car: NO-GO. |
| Q12 | Does the phone request Type111 from the stock Honda session? | `OFFLINE_RESOLVABLE` | P4 | Resolved offline as an inference; NO-GO for observation. |
| Q13 | Raw iAP2 Identification and screen-descriptor bytes | `NOT_JUSTIFIED` | P4 | NO-GO. |
| Q14 | Honda network topology for a future listener (interface, address, route, socket owner) | `NOT_JUSTIFIED` | P3 | NO-GO: meaningless without an authorized receiver path. |
| Q15 | Page-selection arbitration and the waiting/displaying handshake | `AUTHORIZED_SPEC_REQUIRED` | P1 | Spec. Car: NO-GO. |
| Q16 | Software identity of the car versus preserved evidence | `ALREADY_ESTABLISHED` | P2 | NO-GO today; reserved (see section F trigger). |
| Q17 | Archive provenance gaps (original Door Open footage, Sept 18 raw tree, private backup verification) | `OFFLINE_RESOLVABLE` | P2 | GO (offline only, owner action; no vehicle contact). |
| Q18 | Narrow read-only host-log capture of page and status records | `NOT_JUSTIFIED` | P4 | NO-GO. |
| Q19 | Can an ordinary application attach a window on Display 1? | `NOT_JUSTIFIED` | - | PROHIBITED under this campaign and not justified. |

### Per-question detail

#### Q01 — Supported receiver extension for an additional CarPlay display stream

- **Engineering decision affected:** Whether any non-interposing Type111 integration path exists at all (gate RECEIVER_AUTHORIZED_SPEC_REQUIRED).
- **Existing evidence:** Hash-matched static review of the receiver: delegates are compile-time and OEM-internal, no plugin loader, settings readers carry no display keys, no integrator documentation in the preserved set; every working external implementation reviewed uses unsupported in-process interposition (CL-IF-02A).
- **Evidence strength:** HONDA_STATIC_CONFIRMED (negative, bounded to reviewed binaries); vendor documentation UNKNOWN
- **Exact missing fact:** A written statement from the receiver integrator or Honda on whether and how an accessory may obtain an extra display stream, with interface, caller-authorization model and firmware scope.
- **Offline work can answer:** No
- **Parked read-only car observation can answer:** No
- **Physical measurement necessary:** No
- **OEM/integrator specification necessary:** Yes
- **Category:** `AUTHORIZED_SPEC_REQUIRED`
- **Why a car observation cannot replace it:** Only the vendor can state whether a supported mechanism exists; a car observation can show what the stock unit does, never what it is authorized to accept.
- **Candidate collection method:** Owner-authorized written inquiry (draft exists in CL-IF-02A); no vehicle contact.
- **Risk and side effects:** None technical; disclosure and relationship considerations for the owner.
- **Expected useful output:** Yes/no plus interface description and firmware scope.
- **Stop or failure condition:** n/a
- **Priority:** P0
- **Go/No-Go:** Spec inquiry: owner decision. Car: NO-GO.

#### Q02 — Supported Display 1 frame-admission contract

- **Engineering decision affected:** Whether any authorized external producer may supply pixels to the cluster Navigation page (gate DISPLAY_SUPPORTED_PATH_NOT_FOUND).
- **Existing evidence:** No bitmap, surface, file-descriptor or shared-memory parameter exists in any reviewed host Binder/AIDL surface (re-verified this campaign); the renderer service is not bindable; all Display 1 windows are host-owned full-frame roots; the only demonstrated path is private in-process view insertion.
- **Evidence strength:** HONDA_STATIC_CONFIRMED (negative, bounded); OBSERVED_IN_SAVED_EVIDENCE for window ownership
- **Exact missing fact:** An OEM contract: caller authorization, accepted frame type, geometry, page ownership, warning precedence, withdrawal, restoration.
- **Offline work can answer:** No
- **Parked read-only car observation can answer:** No
- **Physical measurement necessary:** No
- **OEM/integrator specification necessary:** Yes
- **Category:** `AUTHORIZED_SPEC_REQUIRED`
- **Why a car observation cannot replace it:** Technical reachability (exported services, generic Android display APIs) is not authorization; observing the factory UI cannot reveal what the host is permitted to admit.
- **Candidate collection method:** Same inquiry as Q01.
- **Risk and side effects:** None technical.
- **Expected useful output:** Contract or written NO-GO.
- **Stop or failure condition:** n/a
- **Priority:** P0
- **Go/No-Go:** Spec inquiry: owner decision. Car: NO-GO.

#### Q03 — Does the stock receiver advertise a second display or alt-screen capability?

- **Engineering decision affected:** Whether Type111 could be offered by the phone without modifying the receiver.
- **Existing evidence:** Single main-screen descriptor builder; the receiver and its proxy library contain none of the alt-screen, view-area, corner-mask, UI-context or related feature vocabulary (zero string hits, hash-matched binaries); Type111 SETUP entries are skipped.
- **Evidence strength:** HONDA_STATIC_CONFIRMED (high); resolved by static inference only; no live /info capture exists
- **Exact missing fact:** Live /info document (non-gating).
- **Offline work can answer:** Yes (done)
- **Parked read-only car observation can answer:** Only with an external inline USB analyzer, which is not owned
- **Physical measurement necessary:** Equipment only
- **OEM/integrator specification necessary:** No
- **Category:** `OFFLINE_RESOLVABLE`
- **Candidate collection method:** None.
- **Risk and side effects:** Link disturbance if a tap were used.
- **Expected useful output:** Would confirm the single-display prediction.
- **Stop or failure condition:** n/a
- **Priority:** P4
- **Go/No-Go:** NO-GO: cannot change any gate; a positive result would contradict high-confidence static evidence.

#### Q04 — Factory host content region and Navigation content bounds in Display 1 coordinates

- **Engineering decision affected:** Sizing of any future Navigation-pane renderer or Type111 VideoConfig request.
- **Existing evidence:** Decoded host layout resources define a base meter region of about 580x270 px at the Display 1 origin; the factory Navigation view set spans about x 60-524, y 0-215 (compass graphics start near y 0; text and route views start near y 23); the saved Display 1 screenshot matches the layout; HondaHack's cast lands at (0,24)-(584,215).
- **Evidence strength:** HONDA_STATIC_CONFIRMED + OBSERVED_IN_SAVED_EVIDENCE (layout variant selection is runtime-inferred)
- **Exact missing fact:** None in Display 1 space, conditional on the runtime-inferred layout variant for this unit. Other models use different regions.
- **Offline work can answer:** Yes (done)
- **Parked read-only car observation can answer:** No
- **Physical measurement necessary:** No
- **OEM/integrator specification necessary:** No
- **Category:** `ALREADY_ESTABLISHED`
- **Candidate collection method:** None.
- **Risk and side effects:** None.
- **Expected useful output:** n/a
- **Stop or failure condition:** n/a
- **Priority:** P2 (record)
- **Go/No-Go:** Closed. Corrects earlier 'no OEM rectangle found' statements, which examined only compiled code, not decoded resources.

#### Q05 — Physically visible region of Display 1 content (observed state)

- **Engineering decision affected:** Viewport bounds a lab renderer should treat as a conservative default.
- **Existing evidence:** Two camera/frame pairs from different poses fit an isotropic, unrotated, unmirrored mapping (residual of a few photo pixels); the cast's vertical span (24-215) is fully visible; Display 1 content is truncated, by native overlay graphics or a panel boundary, on the left (visible from about x 62-75 near the top, 36-48 lower) and right (to about x 544-548 lower, 523-540 near the top). Consistent with the factory Navigation view set and with HondaHack's own 50 px side padding.
- **Evidence strength:** INFERRED from saved evidence (state-specific, +/- about 15 px); not calibrated
- **Exact missing fact:** Calibrated, multi-state measurement; authoritative bounds.
- **Offline work can answer:** Yes (done to estimate precision)
- **Parked read-only car observation can answer:** A fixed-camera photo series could tighten it
- **Physical measurement necessary:** Marginal
- **OEM/integrator specification necessary:** For authority: yes (Q06)
- **Category:** `OFFLINE_RESOLVABLE`
- **Candidate collection method:** None now.
- **Risk and side effects:** Low (photography) but see Q07.
- **Expected useful output:** Tighter tolerance only.
- **Stop or failure condition:** n/a
- **Priority:** P3
- **Go/No-Go:** Offline estimate adopted. Further car data: NO-GO.

#### Q06 — Authoritative CarPlay SafeArea (view areas) for the Honda cluster

- **Engineering decision affected:** The CarPlay-facing geometry contract a receiver would advertise for a cluster display.
- **Existing evidence:** A current iOS phone requests view-area and corner-mask features (third-party lab session); the Honda receiver binaries contain no such vocabulary; no OEM value exists in the preserved set.
- **Evidence strength:** UNKNOWN
- **Exact missing fact:** The receiver-advertised view-area/corner-mask definition for this unit.
- **Offline work can answer:** No
- **Parked read-only car observation can answer:** No (a camera sees the current factory overlay, not a contract)
- **Physical measurement necessary:** No
- **OEM/integrator specification necessary:** Yes
- **Category:** `AUTHORIZED_SPEC_REQUIRED`
- **Why a car observation cannot replace it:** The value is defined by the receiver and advertised to the phone; measuring the cluster cannot create or validate that contract.
- **Candidate collection method:** Part of the Q01 inquiry.
- **Risk and side effects:** None.
- **Expected useful output:** Defined view areas.
- **Stop or failure condition:** n/a
- **Priority:** P1
- **Go/No-Go:** Spec inquiry. Car: NO-GO.

#### Q07 — Variation of native overlay occlusion across cluster states

- **Engineering decision affected:** Whether the Q05 estimate is conservative across states.
- **Existing evidence:** Two states agree within about 5 px; charge/power scale, speed readout and trim states are otherwise unobserved.
- **Evidence strength:** UNKNOWN
- **Exact missing fact:** Fixed-camera frames across several cluster states.
- **Offline work can answer:** Partly (other saved photos)
- **Parked read-only car observation can answer:** Yes (human visual only)
- **Physical measurement necessary:** Photographic
- **OEM/integrator specification necessary:** Overrides if provided
- **Category:** `UNKNOWN`
- **Candidate collection method:** Reserved: fixed-camera photographs across normal cluster states using only existing UI; not proposed now.
- **Risk and side effects:** Low; ordinary UI use.
- **Expected useful output:** Occlusion envelope.
- **Stop or failure condition:** Any warning, freeze, blank or unexpected UI.
- **Priority:** P3
- **Go/No-Go:** NO-GO until Q01/Q06 outcome is known.

#### Q08 — Existing casting follows Navigation page; Stop Casting restores factory Navigation

- **Engineering decision affected:** Whether the lab's page-following and restoration assumptions match the only demonstrated path.
- **Existing evidence:** Owner-reported runtime observations (disappears off Navigation, returns on re-entry, Stop Casting restores); static code makes cast visibility a function of the reported page; the saved factory log is consistent with one additional child in the host's main layer only while casting is active.
- **Evidence strength:** OWNER_REPORTED_RUNTIME_OBSERVATION + HONDAHACK_STATIC + OBSERVED_IN_SAVED_EVIDENCE
- **Exact missing fact:** Nothing decision-changing; it is an unsupported path.
- **Offline work can answer:** Yes (done)
- **Parked read-only car observation can answer:** Not needed
- **Physical measurement necessary:** No
- **OEM/integrator specification necessary:** No
- **Category:** `ALREADY_ESTABLISHED`
- **Candidate collection method:** None.
- **Risk and side effects:** n/a
- **Expected useful output:** n/a
- **Stop or failure condition:** n/a
- **Priority:** P4
- **Go/No-Go:** Closed (owner report plus static evidence). Repeating the camera-only observation is NOT_JUSTIFIED.

#### Q09 — Does the host detach an injected child on page change or stop?

- **Engineering decision affected:** None for an authorized path.
- **Existing evidence:** Static code leaves the child attached on Stop; the saved log shows the child count only at host add-view events.
- **Evidence strength:** HONDAHACK_STATIC
- **Exact missing fact:** Child count at removal events.
- **Offline work can answer:** No
- **Parked read-only car observation can answer:** Yes (host log, ADB)
- **Physical measurement necessary:** No
- **OEM/integrator specification necessary:** No
- **Category:** `NOT_JUSTIFIED`
- **Candidate collection method:** None authorized; any design needs separate review (section F).
- **Risk and side effects:** ADB link state; log content privacy.
- **Expected useful output:** Count transitions.
- **Stop or failure condition:** Zero targets, ambiguous target, unexpected output.
- **Priority:** P4
- **Go/No-Go:** NO-GO: concerns only the unsupported route.

#### Q10 — Warning/interrupt precedence and withdrawal for third-party content

- **Engineering decision affected:** Whether any external pane can be guaranteed to yield to every factory warning.
- **Existing evidence:** Host has a separate interrupt root attached last; one Door Open recording shows preemption and return; the controller-side arbitration is not in the preserved set; raw footage not located.
- **Evidence strength:** HONDA_STATIC_CONFIRMED for host roots; UNPROVEN for precedence
- **Exact missing fact:** Host/controller-owned arbitration guarantee across warning classes.
- **Offline work can answer:** No
- **Parked read-only car observation can answer:** No (warnings must not be induced or awaited)
- **Physical measurement necessary:** No
- **OEM/integrator specification necessary:** Yes
- **Category:** `AUTHORIZED_SPEC_REQUIRED`
- **Why a car observation cannot replace it:** Precedence is a guarantee made by the arbiter; any observation is a sample of one warning class in one state.
- **Candidate collection method:** Part of the Q02 contract.
- **Risk and side effects:** Inducing warnings is prohibited.
- **Expected useful output:** Guarantee.
- **Stop or failure condition:** n/a
- **Priority:** P1
- **Go/No-Go:** Spec. Car: NO-GO.

#### Q11 — Honda Type111 SETUP schema, key derivation, protection profile, VideoConfig

- **Engineering decision affected:** Whether a Type111 stream can be accepted and decoded without guessing.
- **Existing evidence:** Stock SETUP skips Type111 and writes no response; Type110 uses the legacy AES-CTR path; nothing in stock code implements Type111.
- **Evidence strength:** HONDA_STATIC_CONFIRMED (absence); fields UNKNOWN
- **Exact missing fact:** The accepted descriptor/feature schema, SETUP request/response shape, key-derivation inputs, protection profile.
- **Offline work can answer:** No (stock binaries do not implement it)
- **Parked read-only car observation can answer:** No (the stock unit never offers Type111, so a passive trace has nothing to show)
- **Physical measurement necessary:** No
- **OEM/integrator specification necessary:** Yes
- **Category:** `AUTHORIZED_SPEC_REQUIRED`
- **Why a car observation cannot replace it:** A passive capture can only record what a stock session does; the stock session contains no Type111 exchange.
- **Candidate collection method:** Part of the Q01 inquiry.
- **Risk and side effects:** None.
- **Expected useful output:** Schema and crypto contract.
- **Stop or failure condition:** n/a
- **Priority:** P0
- **Go/No-Go:** Spec. Car: NO-GO.

#### Q12 — Does the phone request Type111 from the stock Honda session?

- **Engineering decision affected:** Whether Type111 is reachable at all without modification.
- **Existing evidence:** Single advertised display and absent alt-screen vocabulary imply the phone is not offered a second display; external reports agree the phone follows the advertisement.
- **Evidence strength:** INFERRED (high); resolved by static inference only
- **Exact missing fact:** Live confirmation (non-gating).
- **Offline work can answer:** Yes (done)
- **Parked read-only car observation can answer:** Only with an inline analyzer
- **Physical measurement necessary:** Equipment
- **OEM/integrator specification necessary:** No
- **Category:** `OFFLINE_RESOLVABLE`
- **Candidate collection method:** None.
- **Risk and side effects:** n/a
- **Expected useful output:** n/a
- **Stop or failure condition:** n/a
- **Priority:** P4
- **Go/No-Go:** Resolved offline as an inference; NO-GO for observation.

#### Q13 — Raw iAP2 Identification and screen-descriptor bytes

- **Engineering decision affected:** None currently; the Identification exchange does not carry the secondary-display decision.
- **Existing evidence:** State machine strings only; no on-device capture path (no USB monitor in the kernel).
- **Evidence strength:** UNKNOWN
- **Exact missing fact:** Bytes on the wire.
- **Offline work can answer:** No
- **Parked read-only car observation can answer:** Only with an external inline USB analyzer (not owned)
- **Physical measurement necessary:** Equipment
- **OEM/integrator specification necessary:** No
- **Category:** `NOT_JUSTIFIED`
- **Candidate collection method:** Reserved: passive inline USB capture if an integrator asks for it.
- **Risk and side effects:** Link disturbance; elevated-risk class.
- **Expected useful output:** Packet capture.
- **Stop or failure condition:** Any enumeration anomaly.
- **Priority:** P4
- **Go/No-Go:** NO-GO.

#### Q14 — Honda network topology for a future listener (interface, address, route, socket owner)

- **Engineering decision affected:** Where an authorized secondary-stream listener could bind.
- **Existing evidence:** 43T0-D ended NO-GO twice (zero ADB targets; zero-byte baseline utility stop); earlier real-Honda correlation is partial.
- **Evidence strength:** UNKNOWN / LIKELY_INFERRED for one candidate
- **Exact missing fact:** A complete three-phase read-only delta.
- **Offline work can answer:** No
- **Parked read-only car observation can answer:** Yes (ADB)
- **Physical measurement necessary:** No
- **OEM/integrator specification necessary:** Only after Q01
- **Category:** `NOT_JUSTIFIED`
- **Candidate collection method:** None; the 43T0 contract must not be retried or improvised around.
- **Risk and side effects:** ADB/Wi-Fi state; fallback prohibited.
- **Expected useful output:** n/a
- **Stop or failure condition:** Zero targets or any zero-byte/unexpected result.
- **Priority:** P3
- **Go/No-Go:** NO-GO: meaningless without an authorized receiver path.

#### Q15 — Page-selection arbitration and the waiting/displaying handshake

- **Engineering decision affected:** What authority a pane needs beyond placing a view.
- **Existing evidence:** Host follows a status record from the cluster-controller side; host reports waiting then displaying; selection logic on the controller side is outside the preserved set.
- **Evidence strength:** HONDA_STATIC_CONFIRMED (host half); controller half INFERRED
- **Exact missing fact:** Controller-side arbitration rules.
- **Offline work can answer:** Host half done
- **Parked read-only car observation can answer:** No
- **Physical measurement necessary:** No
- **OEM/integrator specification necessary:** Yes (controller half)
- **Category:** `AUTHORIZED_SPEC_REQUIRED`
- **Why a car observation cannot replace it:** Controller firmware is not in the preserved set and cannot be observed from the Android side.
- **Candidate collection method:** Part of the Q02 contract.
- **Risk and side effects:** Page requests are adjacent to a vehicle-bus path.
- **Expected useful output:** Arbitration contract.
- **Stop or failure condition:** n/a
- **Priority:** P1
- **Go/No-Go:** Spec. Car: NO-GO.

#### Q16 — Software identity of the car versus preserved evidence

- **Engineering decision affected:** Whether preserved artifacts (hash-matched) represent the current unit.
- **Existing evidence:** Software build identifier and model code recorded from the car in saved properties; binaries hash-recorded in private storage.
- **Evidence strength:** OBSERVED_IN_SAVED_EVIDENCE (as of the 2026-09-25/26 snapshot)
- **Exact missing fact:** Currency since the snapshot (only matters for an OEM inquiry).
- **Offline work can answer:** Yes (snapshot)
- **Parked read-only car observation can answer:** Human-visual only (a settings/version screen), no ADB
- **Physical measurement necessary:** No
- **OEM/integrator specification necessary:** No
- **Category:** `ALREADY_ESTABLISHED`
- **Candidate collection method:** Reserved: read the version from the normal UI if an inquiry requires 'current'.
- **Risk and side effects:** Minimal.
- **Expected useful output:** Version string.
- **Stop or failure condition:** Any prompt or unexpected UI.
- **Priority:** P2
- **Go/No-Go:** NO-GO today; reserved (see section F trigger).

#### Q17 — Archive provenance gaps (original Door Open footage, Sept 18 raw tree, private backup verification)

- **Engineering decision affected:** Whether prior claims can be re-verified from primary evidence.
- **Existing evidence:** Footage not located (also noted by CL-R10B); Sept 18 captures found under a separate Documents tree; backup/recovery unverified.
- **Evidence strength:** UNKNOWN
- **Exact missing fact:** Locate and hash; verify backup.
- **Offline work can answer:** Yes (owner-local)
- **Parked read-only car observation can answer:** No
- **Physical measurement necessary:** No
- **OEM/integrator specification necessary:** No
- **Category:** `OFFLINE_RESOLVABLE`
- **Candidate collection method:** Owner locates files; hash into the private manifest.
- **Risk and side effects:** None.
- **Expected useful output:** Primary-evidence pointers.
- **Stop or failure condition:** n/a
- **Priority:** P2
- **Go/No-Go:** GO (offline only, owner action; no vehicle contact).

#### Q18 — Narrow read-only host-log capture of page and status records

- **Engineering decision affected:** None for the authorized path (see Q09).
- **Existing evidence:** The host service logs page/status records at INFO under its own tag; the logger is observed emitting in saved captures, but no page/status record was observed; the status-data text format is not decompiled; the stream also carries unrelated metadata (for example track titles).
- **Evidence strength:** HONDA_STATIC_CONFIRMED (tag, level, strings); expected output format UNKNOWN
- **Exact missing fact:** Output format of the status record.
- **Offline work can answer:** Mostly (format outstanding)
- **Parked read-only car observation can answer:** Yes (ADB)
- **Physical measurement necessary:** No
- **OEM/integrator specification necessary:** No
- **Category:** `NOT_JUSTIFIED`
- **Candidate collection method:** None authorized; any design needs separate review (section F).
- **Risk and side effects:** ADB link; log privacy; format unknown.
- **Expected useful output:** Page/status transitions.
- **Stop or failure condition:** Zero or ambiguous target; any output outside the filter.
- **Priority:** P4
- **Go/No-Go:** NO-GO.

#### Q19 — Can an ordinary application attach a window on Display 1?

- **Engineering decision affected:** None; reachability is not authorization.
- **Existing evidence:** Generic Android display APIs exist; Honda admission policy unknown.
- **Evidence strength:** UNKNOWN
- **Exact missing fact:** -
- **Offline work can answer:** No
- **Parked read-only car observation can answer:** Only by attempting it, which is runtime display injection
- **Physical measurement necessary:** No
- **OEM/integrator specification necessary:** Yes
- **Category:** `NOT_JUSTIFIED`
- **Candidate collection method:** None; prohibited.
- **Risk and side effects:** Alters Honda-owned display state.
- **Expected useful output:** n/a
- **Stop or failure condition:** n/a
- **Priority:** -
- **Go/No-Go:** PROHIBITED under this campaign and not justified.

## F. Proposed next car session

**None is proposed.** For every `CAR_EVIDENCE_REQUIRED` question the proposal would name the engineering decision it unlocks; there are none. For every `AUTHORIZED_SPEC_REQUIRED` question (Q01, Q02, Q06, Q10, Q11, Q15) the rationale for why another car observation cannot replace the authorization is recorded in the matrix.

Held in reserve, each `NO-GO` today and requiring its own review and authorization if a trigger occurs:

| Candidate | Class | Trigger | Why not now |
|---|---|---|---|
| Fixed-camera photographs across normal cluster states using only existing UI (Q07) | Human visual | An OEM/integrator reply that still needs measured occlusion, or a decision to size a lab renderer from measurement | Does not change any gate; estimate exists. |
| Version-screen read from the normal UI (Q16) | Human visual | An inquiry that must cite the current software version | Snapshot identity already recorded. |
| Host-log read (Q09/Q18) | Not approved; reserved | A future authorized design that depends on host page/status semantics | Output format unverified offline; answers nothing for an authorized path; ADB route failed twice in 43T0. |
| Passive inline USB capture (Q03/Q12/Q13) | Elevated-risk, external equipment | An integrator asks for it | Equipment not owned; cannot change a gate. |

Prohibited or not justified: any Binder call (including getter-named control APIs), window attachment or other display injection (Q19), inducing or waiting for warnings, repeating the camera-only observation, retrying the 43T0 network delta or improvising around its stopping rules, installing software, changing settings, and any live Type111 or receiver experiment.

### ADB assessment

ADB is **not** recommended for a future session. The reassessment did identify a narrowly attributable host log source (N4), which corrects the earlier statement that none existed. It is rejected because (a) no gate-relevant decision depends on its content, (b) the expected output format of the status record is not verifiable offline, (c) the same stream carries unrelated metadata that would require host-side filtering, and (d) the ADB route has failed twice under the 43T0 contract, whose zero-byte stopping rule must not be bypassed. If a later authorized design makes page/status semantics decision-relevant, a separately reviewed, host-filtered, read-only log read can be specified then; nothing here approves it.

## G. Human operator runbook

None. No activity is independently approved. The envelope below applies to **any** future activity that is separately reviewed and authorized; it is not itself an authorization.

- **Before:** vehicle parked with parking brake set; normal center and cluster UI confirmed; no warnings present; recording equipment placed outside the cluster and not touching it; private storage ready; the approved activity list and stop conditions read aloud.
- **During:** only the listed actions, once, in order; no exploration of anomalies; no repeated attempts.
- **Sufficient evidence:** the stated success criterion for each action has been met once; stop collecting immediately.
- **Stop at once on:** any warning or interrupt, freeze or blank display, unexpected prompt or UI, host restart, camera obstruction, any uncertainty about state, zero or ambiguous diagnostic target, or any zero-byte/unexpected command output.
- **Closing:** return any ordinary UI state to normal using only the normal controls; the operator reports what was **observed**, separately from what was **intended**. A failed restoration is recorded as unverified and is not repaired under the same approval.
- **Authorization:** no part of this runbook may be executed without separate written authorization.
- **Shutdown:** the operator may follow the vehicle's normal shutdown procedure as soon as collection ends. File processing happens offline afterward and does not require the car to remain powered.

## H. Evidence handling and publication

- New derived evidence lives in an explicitly private directory outside every Git worktree (mode 0700). Non-video diagnostics must not be forced into the CL-OBS-02 video-only schema; a text-diagnostic bundle in the style of the 43T0 collectors (allowlisted commands, manifest with hashes, owner-only files) is the appropriate model if one is ever authorized.
- Nothing in this document reproduces raw captures, resource files, binaries, identifiers, function names, hashes, endpoints or media. Geometry figures are rounded aggregate measurements.
- Review: the findings were self-reviewed against the private manifest. Automated ECC agent review is recorded in the pull request; it is not independent human approval, and none is claimed.

## Limits

This record does not establish that the Honda can admit a Type111 stream or a third-party Display 1 frame, any OEM SafeArea or warning-precedence guarantee, physical restoration in any state beyond the owner's report, or any vehicle safety property.
