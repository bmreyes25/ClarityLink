# CL-HONDA-111-01 / M7 — Next observation plan (UNEXECUTED PROPOSAL)

**Status: proposal only. Nothing here is authorized, scheduled or performed.** This campaign ran no vehicle ADB, no connection to the car, no live iPhone session and no instrumentation. `safeForHonda() == false`. Any step below needs separate, written owner approval for that exact step and an independent review before it starts. Approval for one step does not extend to another.

## 0. What an observation can and cannot do

Neither critical gate is held up by a missing measurement alone. Gate 1 needs a supported extension boundary and the Type111 facts only the factory code's owner can supply; Gate 2 needs an authorized caller contract. **No observation here can turn either gate to GO.** Their purpose is narrower: remove unknowns that any future authorized contract would need, and test two assumptions the synthetic models make. Each question below says which assumption its answer would confirm or break.

## 1. Do these offline first (no vehicle)

| ID | Task | Why it comes first |
|---|---|---|
| P1 | **DONE in this campaign.** A bounded static trace of the Out service's content manager. Result: the cluster controller selects the page and the host follows a steering-switch status record, acknowledging with a waiting-then-displaying handshake; a changed selection resumes an existing screen or clears the host's own screens. See section 2a of the [Navigation-pane contract](../../research/honda/cl-honda-111-01-navigation-pane-contract.md). | Answered who selects the page and what the host does on a change. It did not and cannot answer whether an *injected* View is removed. |
| P2 | Reproduce the HondaHack string decode inside the HondaHack-Research tree so its unresolved item U-13 can be closed on independent evidence (evidence-map C1). | Removes a provenance caveat. |
| P3 | A non-vehicle written request to the owner of the factory code (and, separately, HondaHack's maintainer) for a documented extension or frame-admission contract and exact supported model/firmware scope. | The only thing that can change Gate 1 or Gate 2 from NO-GO. Not an engineering experiment. |

P1 narrowed Q2 (the mapping is now a status record, not a guess) but did not remove Q1: whether injected Views follow a page change is exactly what static code of the host cannot show.

## 2. Decision-changing questions, ordered by information value

### Q1 — Does injected content actually follow Navigation-page selection and restore factory content?

| Field | Content |
|---|---|
| Exact question | During ordinary driver-controlled page changes, does the already-installed Screen Casting feature (a) stay visible only on the Navigation page, (b) disappear immediately on leaving it, (c) return only on re-entry, and (d) leave the factory page fully intact after "Stop Casting"? |
| Why existing evidence is insufficient | The preserved captures are not synchronized to page changes. Static code shows the overlay's *visibility rule* and that Stop Casting leaves the view attached, but not what the host does to its own Views on a page change. |
| Data required | A synchronized external video of the center display and the cluster, with a common audible or visible marker, across: enter Navigation, leave, re-enter, Stop Casting, return to factory Navigation. No Android data. |
| Sensitivity | The recording shows the vehicle's cluster and may show location or trip data on screen. Treat as private; do not publish raw video. |
| Class | **Passive.** Uses the existing feature through its existing UI. No ADB, no install, no setting change. |
| Preconditions | Vehicle parked, engine state per owner's choice, brake applied, no driver distraction, a second person recording, existing feature already enabled by the owner before the session, camera fixed on a stand. |
| Independent review | Required for the written procedure. |
| Owner approval | Required, written, for this procedure only. |
| Time bound | One session, at most 20 minutes of recording. |
| Stop conditions | Any warning appears; the cluster or center display freezes or blanks; the display process restarts; factory content does not return after Stop Casting; any unexpected prompt. On stop: end casting through the existing UI, stop recording, do nothing else. |
| Restoration verification | Factory Navigation shown normally on the cluster and center CarPlay/UI normal, confirmed on video. |
| Retention and redaction | Raw video private. Published result: a sanitized table of page-change versus visible/not-visible, no frames of the car interior or route. |
| What it would change | Confirms or breaks the assumption behind `observe_contents` (visibility follows the page). If content stays visible off-page, the pane contract must treat the page signal as insufficient and detach explicitly; if stop leaves anything behind, the restoration rule moves from "revoke" to "revoke and verify". |

### Q2 — What contents identifier and status does the host report during those same page changes?

| Field | Content |
|---|---|
| Exact question | Which (contents id, status) pairs does the host report for Navigation, other pages, interrupts and a stopped cast, and in what order? |
| Why existing evidence is insufficient | Static code defines the scheme and HondaHack consumes it, but the runtime sequence and the meaning of "status none" are unobserved. |
| Data required | The host's own debug log lines for page and interrupt transitions, only if the host emits them. No properties, packages, accounts, device identifiers or trip data. |
| Sensitivity | Logs may carry location or phone data. Filter at capture to the host's tag and discard everything else. |
| Class | **Read-only, but requires opening a new vehicle ADB session.** That is the sensitive part: the connection itself, not the command. This campaign did not do it. |
| Preconditions | Q1 approved and run first (so the log can be paired with the video); a separately reviewed capture command limited to reading one log tag; a pre-agreed disconnect step. |
| Independent review / owner approval | Both required, written, specific to the exact command. |
| Time bound | The same single Q1 session; at most one capture window. |
| Stop conditions | Any output that is not the filtered tag; the ADB connection reports an unexpected target or identity; a warning appears; any permission prompt. Disconnect immediately. |
| Restoration verification | ADB disconnected; vehicle state as before; no files left on the head unit. |
| Retention and redaction | Private. Published result: the transition table only. |
| What it would change | Confirms or corrects the mapping used by `observe_contents` (which class and status select the page, how a warning appears, whether a silent host is a real condition). It could show the host does not log these transitions, which would remove the cheaper route and leave only the video. |

### Q3 — What is the physical visible aperture for a given Display 1 content?

| Field | Content |
|---|---|
| Exact question | For a known, uniquely marked Display 1 test pattern shown by an existing mechanism, which part of it is visible on the physical cluster, and where? |
| Why existing evidence is insufficient | The existing pair shows that the physical cluster has indicators absent from Display 1 but has no scale reference or calibrated transform. The earlier note records that repeating the same uncalibrated capture is not useful. |
| Data required | One photograph or short clip with a rigid scale or grid reference attached beside the cluster, framed square-on, plus the exact content shown at that moment. |
| Sensitivity | Low. The pattern is generic. |
| Class | **Passive**, if the pattern comes from the existing casting feature through its UI; otherwise it would need new content and is not proposed here. |
| Preconditions | Q1 passed without incident; scale reference attached without touching the cluster. |
| Review / approval | As above. |
| Time bound | Ten minutes inside the Q1 session. |
| Stop conditions | As Q1. |
| Restoration verification | Reference removed; factory page normal. |
| What it would change | Provides the first non-synthetic input to `Viewport` with an `AUTHORITATIVE_MEASURED` source. It would still be a measurement of one state, not an OEM safe-area guarantee. |

## 3. Explicitly out of scope

- Inducing or waiting for warnings of any class.
- Any command that writes, installs, hooks, injects, changes settings, sends an interrupt or page request, or touches the receiver, the authentication session, CAN, firmware or the cluster.
- Capturing, recording or inferring keys, pairing data or protected media.
- Connecting a live iPhone to anything other than the owner's normal use of the car.
- A second CarPlay session or any extra receiver.

## 4. Approval packet required before any step

Exact step list with the question each answers, the full command or procedure text, equipment, filtering and redaction plan, stop conditions, restoration check, operator, reviewer, and the explicit statement that `safeForHonda()` remains false. Approval for Q1 is not approval for Q2 or Q3.
