# CL-OBS-02 — Parked passive Display 1 observation proposal

**Proposal only. This document is not authorization. No vehicle session or ADB command has been run. `safeForHonda() == false`.** A future session requires separate written owner authorization for this exact procedure and independent review of the final run plan and stop/restoration criteria.

## Recommendation

One short, passive, fixed-camera observation is justified to answer the remaining page-visibility/restoration question and, only if an already-existing feature presents a known marked pattern, obtain a calibrated physical-aperture sample. Do not add an ADB phase: the reviewed offline evidence does not identify a narrow page/status log tag or exact log statement, so no safe exact filter can be specified. No warnings are induced or awaited.

## Exact questions and value

| Item | Proposal |
|---|---|
| Q1: exact unknown | In ordinary parked use of the already-enabled HondaHack casting feature, does content appear only while the factory Navigation page is selected; what is visible immediately after leaving and re-entering Navigation; and does using the existing Stop Casting UI return the physical cluster to normal factory Navigation content? |
| Why existing evidence is insufficient | Static host code describes factory page callbacks but cannot establish what the private injected child does when the host changes pages. Existing private recording summaries cover one Door Open interruption, not a synchronized Navigation page transition and stop/restore sequence. Stop Casting is statically known to leave the injected view attached, so physical restoration cannot be inferred from the button label. |
| Q3: exact unknown (conditional) | If the existing UI can show a known uniquely marked pattern without changing settings or software, which pixels/region of that pattern appear in the physical cluster aperture, relative to a calibrated scale? |
| Why existing evidence is insufficient | 800×480 describes logical Display 1; 584×191 is HondaHack layout-local. Neither supplies a physical transform or aperture boundary. Previous uncalibrated images cannot resolve that mapping. |
| Decision changed | Q1 confirms or breaks the synthetic `PaneLease` assumption that visibility tracks Navigation selection and informs whether stop must include independent restoration verification. Q3 supplies one calibrated observed transform for the tested state. Neither can establish external frame admission, supported status, OEM SafeArea, general warning priority, or authorization. |

## Procedure for separate approval

1. Vehicle remains parked for the full session, with the parking brake set. Use the owner's preferred vehicle state; do not change vehicle settings for this observation.
2. The owner/operator confirms the existing casting feature is already configured and visible through its normal UI. Do not install, enable a new hook, change a property, or start an unfamiliar feature.
3. A second person positions a fixed external camera square-on to include the physical cluster only. Keep a rigid scale/grid reference beside the cluster without touching the cluster or obstructing any display. Use a common visible/audible spoken marker to align the recording with each normal UI action.
4. In one pass, record: normal factory Navigation with casting off; start casting via its existing UI; select another existing factory page using normal driver controls; return to Navigation; stop casting using the existing Stop Casting UI; verify normal factory Navigation content is visible again. Do not repeat or explore alternate states.
5. Include the geometry sample only if a known marked pattern is already available via that same existing UI and can be shown without changing configuration. Otherwise omit Q3.
6. Stop the recording after the restoration check. No ADB, screenshots from the head unit, device/app introspection, Binder calls, warnings, route entry, CarPlay pairing, or additional commands.

## Classification, equipment and limits

- **Class:** Passive camera observation of existing UI and normal factory page controls. It has no planned software/system writes. Human page selection and existing casting UI actions can change the displayed page or casting state, so this is not a no-op observation.
- **Equipment:** Fixed external camera with adequate focus/exposure; rigid scale/grid that stays outside the cluster aperture; one operator and one observer/recorder. No vehicle connection cable or diagnostic equipment.
- **Bound:** One session, one transition sequence, at most 10 minutes of recording. Do not extend to investigate anomalies.
- **Expected outcomes:** (1) Content disappears off Navigation and returns on re-entry: supports the visibility assumption for this exact feature/state only. (2) Content remains visible off-page or fails to return: assumption is false; any future design needs an independently authorized host-owned state/revoke contract. (3) Stop Casting returns factory Navigation: observed restoration for this path/state only. (4) content remains, cluster is blank/frozen, or factory Navigation does not return: stop immediately; restoration is unverified and no further steps are allowed. (5) Pattern crop can be measured: retain a calibrated sample for this state; it is not an OEM SafeArea. (6) no known pattern is available: Q3 remains open.
- **ADB:** Not included. Exact target identity, allowlist, and log tag cannot be specified because a target page/status log record has not been established offline. No broad log collection is acceptable.

## Stop and restoration conditions

Stop immediately on any warning/interrupt appearing, unexpected prompt, freeze/blank display, host restart, casting content visible on a non-Navigation page, unexpected UI, camera obstruction, or any uncertainty about the current feature/page state. Do not induce, wait for, or dismiss a warning as part of the protocol. Use only the existing Stop Casting UI if responsive, end recording, and do not issue diagnostic or recovery commands. If normal factory Navigation and normal center-display UI are not visibly restored promptly through the existing UI path, end the session and report restoration unverified; do not attempt a second fix.

Before calling the observation successful, the recording must show existing casting stopped, factory Navigation visible normally on the physical cluster, and the normal center display UI. This is visual evidence for that session, not proof of host crash recovery or universal restoration.

## Privacy, review and retention

The recording may contain the vehicle interior, warning indicators, trip/location information, or identifying reflections. Keep raw media in the owner's approved private storage; do not add it to this repository, public Git, PRs, or shared research folders. Review privately and retain only a manually sanitized transition table and, if separately approved, a de-identified geometry measurement. Redact or discard frames containing location, personal information, or identifiers. Delete the raw recording under the owner's approved retention rule after the private review. Do not create a recording until the owner approves the exact written plan and an independent reviewer approves its stop and restoration criteria.

## Explicit limits

This observation cannot prove that a normal app may attach a window, that HondaHack is authorized, that any Binder is supported, that a custom pane will preempt all warnings, that page selection is readable by an external app, or that camera-derived geometry is CarPlay SafeArea. It does not change `DISPLAY_SUPPORTED_PATH_NOT_FOUND`.
