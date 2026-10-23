# CL-OBS-02 independent safety review packet

**For the independent qualified reviewer. This packet does not authorize a vehicle session and records no approval.** `safeForHonda() == false`. `RECEIVER_AUTHORIZED_SPEC_REQUIRED`, `DISPLAY_SUPPORTED_PATH_NOT_FOUND` and `VEHICLE_SESSION_NOT_AUTHORIZED` are unchanged.

ECC and other AI reviews of this material are software and documentation checks. They are **not** an independent qualified vehicle-safety review and must not be recorded as one. If no qualified reviewer is available, the session stays `VEHICLE_SESSION_NOT_AUTHORIZED`.

## 1. What is being reviewed

| Item | Content |
|---|---|
| Purpose | One parked, passive, fixed-camera observation of existing Screen Casting on the factory Navigation page: does cast content follow Navigation selection, and does the existing Stop Casting UI return factory Navigation. It answers a design question for an offline model. It establishes no supported CarPlay integration, frame admission, OEM approval, warning priority, host crash recovery or SafeArea. |
| Scope | One session, one transition sequence, at most 10 minutes of recording, vehicle parked with the parking brake applied. No retry under the same approval. |
| Controlling procedure | [Operator packet](cl-obs-02-operator-packet.md) and [preflight packet](cl-obs-02-preflight-packet.md) sections 3 to 6 at the PR #89 head SHA you review, plus the PR #87 proposal at `fc4623f9e0b7798f9f3f335f2ca4d5d448bdc799` (blob `21d126c40637575f49f2eff68c23bcdcd7d70cee`, still the PR #87 head when this was written). If they disagree, the stricter text governs. |
| Evidence rules | [Evidence acceptance](cl-obs-02-evidence-acceptance.md) |
| Not in scope | Everything in [preflight section 9](cl-obs-02-preflight-packet.md#9-explicitly-excluded): ADB, live iPhone, receiver or Xposed changes, APK install, private Binder calls, CAN, firmware or system writes, framebuffer injection, warning induction, injected patterns, route entry, CarPlay pairing, head-unit screenshots, repeat or exploratory runs, cloud upload. |

## 2. Operator actions (complete list)

Only these, all through existing factory or HondaHack controls the owner already uses:

1. Start the camera (recorder).
2. Start casting with the familiar casting UI.
3. Select one pre-agreed other factory page with the normal page control.
4. Select Navigation again (only if cast content was not visible off Navigation).
5. Press the normal Stop Casting control (once).
6. Speak the markers `BASELINE`, `CAST_ON`, `PAGE_AWAY`, `PAGE_BACK`, `CAST_OFF`, `RESTORED_CHECK`, `CENTER_NORMAL` or `CENTER_ABNORMAL`, `END`, and `STOP` on a stop condition.

No setting, software, property, cable or diagnostic interaction. No warning is induced, waited for or dismissed.

## 3. Roles and equipment

- Operator (owner or designee): performs the actions above, speaks markers, watches the center display. The vehicle stays parked, parking brake on.
- Recorder (second person): runs the camera and a visible timer, calls the 8:00 and 10:00 marks.
- One fixed camera, optional rigid scale (only if a known pattern is already shown), visible timer. Nothing connects to the vehicle.

## 4. Expected display states

| Step | Expected | Alternatives that are recorded, not fixed |
|---|---|---|
| Baseline | Casting off, factory Navigation idle content, center display normal | Any other state: do not start |
| Cast on | Cast content in the Navigation region | None, blank or partial after 30 s: skip to Stop Casting |
| Other page | Factory page shown, cast content gone | Cast content still visible: **stop condition** |
| Back to Navigation | Cast returns, or factory Navigation without cast | Stale or blank: recorded, then continue to Stop Casting |
| Stop Casting | Looks like the baseline | Residue or alternate layout (static analysis predicts this may happen): session ends as restoration failed or unverified, no second attempt |

## 5. Stop conditions and restoration

Stop immediately on: any warning or interrupt, unexpected prompt or UI, frozen or blank display, host restart, cast content visible off Navigation, camera obstruction or failure, 10:00 elapsed, any uncertainty about page or casting state. On a stop: say `STOP`, press the normal Stop Casting control once if casting is on and it responds, hold the camera on the cluster about 10 s, end the recording. No retry, no diagnostic, no repair attempt.

Restoration is accepted only when the recording shows casting off and factory Navigation visible as in the baseline, and the operator's spoken center-display marker is normal. If not restored promptly through the existing UI, the session ends. Any later recovery is a separate owner decision with its own review. Classification meanings are in the [evidence acceptance rules](cl-obs-02-evidence-acceptance.md#3-session-classes).

## 6. Privacy

Raw media stays in owner-approved private storage outside every Git work tree, sealed with SHA-256 and kept read-only. Nothing is uploaded. Only a manually written, de-identified text summary may be published. No VIN, phone identifier, GPS or account data is recorded in notes. Private storage location approval is a separate owner item ([rehearsal and storage](cl-obs-02-camera-rehearsal.md)).

## 7. Known limitations

- Camera video shows only the cluster. Center-display normality is an operator's spoken marker: lower confidence, not video proof.
- Q8 geometry is optional and may be `GEOMETRY_NOT_TESTED`. Camera-derived geometry is never an OEM or CarPlay SafeArea.
- The tool and tests are offline bookkeeping. The evidence system is not tamper-proof; see [residual risks](cl-obs-02-evidence-acceptance.md#7-residual-risks-and-assumptions).
- A real-camera rehearsal has not been performed. Camera placement and conditions at the vehicle are unverified.
- Static analysis predicts Stop Casting may leave the injected view attached with an alternate layout, so non-restoration is a plausible outcome. The plan treats it as a recorded result, not something to fix on the spot.

## 8. Decisions requested from the reviewer

Each needs an explicit APPROVE or REJECT, with conditions. ECC's recommendation below is an input, not an approval.

**R-1. Center display: spoken marker or in frame?**
- Options: (a) cluster-only frame plus spoken `CENTER_NORMAL`/`CENTER_ABNORMAL` at start and end; (b) wider frame including the center display (video proof, but cluster detail drops and the center display may show location or other private content); (c) second camera on the center display (more equipment and mounting risk).
- Information gained: (a) operator attestation only; (b)/(c) independently reviewable video of center-display state.
- Least-invasive option that gives sufficient cluster evidence: (a).
- Question: "Is a spoken marker sufficient evidence of center-display normality, or must the center display be in a recorded frame?"

**R-2. One normal Stop Casting before recording?**
- Applies only if casting is already on at arrival. The default plan is: do not start.
- Gained by allowing it: avoids losing the session. Cost: an unrecorded vehicle interaction, and the baseline then reflects a post-stop state which, per static analysis, may not equal a clean factory Navigation state.
- Recommendation: not allowed. Do not introduce it without this approval.
- Question: "May the operator press the normal Stop Casting control once, unrecorded, before the baseline, if casting is on at arrival?"

**R-3. Camera mount.**
- Constraints to confirm: the camera and any support must not obstruct the driver's view of the road, gauges, warnings or controls; must not touch or attach to the instrument cluster, steering wheel, steering column controls or airbag cover; must not alter steering wheel position; must be stable if the vehicle is bumped.
- Options: (a) free-standing tripod or stable support on the passenger side, not attached to the vehicle, slightly off-axis; (b) clip or suction mount on the dash or windshield outside the driver's sight lines; (c) handheld by the recorder (no attachment, but motion and obstruction risk).
- Recommendation: (a). A square-on view for Q8 may need the driver's sight line; if so, skip Q8 rather than place the camera there.
- Question: "Approve this specific camera position and support, or specify another."

## 9. Reviewer record

| Field | Value |
|---|---|
| Reviewer name and qualification | PENDING (filled by the reviewer, never by the assistant) |
| PR #89 head SHA reviewed | PENDING |
| R-1 / R-2 / R-3 decisions | PENDING |
| Conditions | PENDING |
| Signature and date | PENDING |

Approval binds only to the SHA reviewed. Any later edit voids it. This document, the tool's `independent_safety_review` field and passing CI never constitute approval.
