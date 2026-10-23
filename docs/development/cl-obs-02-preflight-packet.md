# CL-OBS-02 preflight packet

**Preparation only. This packet does not authorize a vehicle session.** No vehicle, ADB, iPhone, receiver, Xposed or installation step was performed to produce it. `safeForHonda() == false`. `RECEIVER_AUTHORIZED_SPEC_REQUIRED` and `DISPLAY_SUPPORTED_PATH_NOT_FOUND` remain open and are not affected by anything here.

Without all three approvals in [section 8](#8-approval-packet) the status is `VEHICLE_SESSION_NOT_AUTHORIZED`.

- **Controlling scope:** the CL-OBS-02 proposal in [PR #87](https://github.com/bmreyes25/ClarityLink/pull/87), file `docs/development/cl-obs-02-parked-observation-proposal.md` at PR head `fc4623f9e0b7798f9f3f335f2ca4d5d448bdc799` (blob `21d126c40637575f49f2eff68c23bcdcd7d70cee`). That file is not on `main` until PR #87 merges, so it is cited by revision rather than linked. This packet only clarifies it. If the two disagree, the stricter text governs and the disagreement is a defect to fix before approval.
- **Companion:** [evidence acceptance rules](cl-obs-02-evidence-acceptance.md), [vehicle testing boundaries](../safety/vehicle-testing.md), [observation gate](vehicle-observation-gate.md), [evidence labels](evidence-classification.md).
- **Context (not re-derived):** PR #88 (CL-IF-02A, Type111 receiver discovery, `NO_SUPPORTED_PATH_FOUND_IN_REVIEWED_SCOPE`), PR #80 (Navigation-pane contract), PR #87 (display-host discovery). Their findings are references, not current acceptance results.

The observation is **one parked session, one transition sequence, at most 10 minutes of recording**.

## 1. Question-to-evidence matrix

Evidence labels follow [evidence classification](evidence-classification.md). "Field" is the observation-record field in the acceptance document. "Without ADB" is yes for every question; no ADB is planned.

| Q | Question | Required observable | Recording state | Operator action | Expected / alternatives | Contradicts synthetic `PaneLease` assumption if | Existing evidence | Still unknown afterwards | Field |
|---|---|---|---|---|---|---|---|---|---|
| Q1 | What does factory Navigation look like before casting? | Cluster Navigation page, casting off, steady for about 10 s | Recording; marker `BASELINE` | Select Navigation with the normal control (before recording) | Idle Navigation content, e.g. compass/grid and menu | None directly; it is the reference for Q5 | `HYPOTHESIS`-grade: historical session summary shows one earlier factory Navigation image, not this state | Appearance in other vehicle states | `baseline_recorded` |
| Q2 | Does existing Screen Casting appear correctly with Navigation selected? | Cast content in the Navigation region | Recording; marker `CAST_ON` | Start casting through its familiar UI | Content appears; or no content / blank / partial | Content never appears, or appears outside the Navigation page | Historical: the private path has appeared on the cluster; not paired with page selection | Frame admission, ownership, supportedness | `casting_on_navigation` |
| Q3 | Does casting disappear when another factory page is selected? | Cluster after one page change | Recording; marker `PAGE_AWAY` | Select one pre-agreed existing page with the normal control | Cast content gone, factory page shown; or cast content still visible | **Cast content remains visible off Navigation** (visibility does not track selection) | None for this transition (static trace: host clears its own screens; injected child unknown) | Behavior on other pages or controls | `page_exit_result` |
| Q4 | What happens when Navigation is selected again? | Cluster after re-selecting Navigation | Recording; marker `PAGE_BACK` | Select Navigation with the normal control; only if Q3 was normal | Cast returns; or factory Navigation without cast; or stale/blank | Stale frame, cast absent while casting is on, or blank | None | Whether this repeats; generation handling | `page_reentry_result` |
| Q5 | Does Stop Casting restore factory Navigation? | Cluster after Stop Casting; compare with Q1 | Recording; marker `CAST_OFF` then `RESTORED_CHECK` | Press the normal Stop Casting control | Looks like the Q1 baseline; or alternate layout / residue remains (static code says the view stays attached) | Anything other than the baseline appearance | None at runtime | Host crash recovery, other warning classes | `stop_casting_result`, `restoration_result` |
| Q6 | Does the center display keep operating normally? | Center display responds and looks normal throughout | **Not in camera frame.** Operator speaks `CENTER_NORMAL`/`CENTER_ABNORMAL` at start and at the end | Glance and speak; no input needed | Normal; or any abnormality (then stop) | n/a | Historical note: center display mirrored by casting in earlier sessions | Continuous behavior between checks | `center_display_normal` |
| Q7 | Any stale image, cropping, overlap or failure to restore? | Visual review of every segment | Recording; no extra step | None | None seen; or anomaly with timestamp | n/a (any anomaly informs the lease model) | None | Anomalies outside the camera's view or too fine for the video | `stale_crop_overlap_anomaly` |
| Q8 | Physical Navigation aperture, if a known pattern already exists? | Known marked pattern plus a rigid scale in one square-on frame | Recording; marker `GEOMETRY` | None beyond Q2 | Measurable crop; or `GEOMETRY_NOT_TESTED` | Aperture differs materially from the 584×191 layout-local assumption | None (800×480 is logical; 584×191 is layout-local) | OEM SafeArea; CarPlay SafeArea; other states | `geometry` |

A successful session resolves Q1 to Q7 for this vehicle state and feature, and Q8 only when a known pattern already exists. It does **not** establish frame admission, OEM approval, warning priority, host crash recovery, or a SafeArea.

## 2. Audit of the PR #87 procedure

Findings are corrections or tightenings for this packet. None adds a test or an action.

| ID | Finding in the proposal | Resolution in this packet |
|---|---|---|
| F-1 | "Owner's preferred vehicle state" does not define a startup state. | Record the state (parked, parking brake on, ignition/accessory state as the owner normally uses for casting) in the private notes. Do not change it for the test. If it differs from what the owner normally uses, do not start. |
| F-2 | Proposal says "cluster only" for the camera but also requires the center display to be verified; the center display is not in that frame. | Center-display normality is an operator's spoken marker on the recording, not a video observation. It is lower-confidence evidence and is labeled that way. Widening the frame would reduce cluster detail and is an owner/reviewer decision (R-1). |
| F-3 | "Select another existing factory page" does not say which. | The owner names one page in advance and writes it in the approval record. It must be reachable by the normal page control alone, with no menu, confirmation or setting change. |
| F-4 | Return-to-Navigation is unconditional in the text. | It is conditional on a normal Q3 result. If casting is visible off Navigation, stop. |
| F-5 | The casting-off baseline is assumed. | The operator confirms casting is off and factory Navigation is shown before recording. If casting is already on, do not start (R-2 lets the reviewer permit one normal Stop Casting before recording; default is no start). |
| F-6 | Static analysis says Stop Casting leaves the injected view attached with an alternate layout, so "restored" may legitimately fail. | Both outcomes are recorded. A non-restored result ends the session as `RESTORATION_UNVERIFIED`; the operator does not retry, toggle, or fix. Any later recovery is a separate owner decision outside this packet. |
| F-7 | No timer rules. | A visible timer starts with the recording. At 8:00 skip to Stop Casting. At 10:00 stop the recording even if steps remain. |
| F-8 | "Common marker" is undefined. | Fixed marker vocabulary (section 4). |
| F-9 | Camera mount safety is not stated. | The mount must not touch the cluster, steering controls or airbag cover, and the steering wheel position must not change during the session. The safety reviewer confirms the mount (R-3). |
| F-10 | Approval has no version binding. | Section 8 binds approval to a PR head SHA; any later edit voids it. |
| F-11 | A stopped session could be retried under the same approval. | One session per approval. A stop or abort is final for that approval. |

Allowed actions are exactly the normal UI actions listed in section 4. Everything in [section 9](#9-explicitly-excluded) is excluded.

## 3. Before recording

Do not improvise a repair or configuration change for any failed item. A failed item means **do not start**; record `NOT_TESTED` with the reason.

- [ ] Written owner authorization, independent qualified safety review, and operator's confirmation that they read the stop procedure are recorded against the approved version (section 8).
- [ ] Vehicle parked securely, parking brake applied, state recorded per F-1.
- [ ] Existing casting feature already configured and familiar; nothing to install, enable or change.
- [ ] Casting is off and factory Navigation is shown normally on the cluster.
- [ ] Center display appears normal.
- [ ] No abnormal vehicle warning or unexpected prompt.
- [ ] Camera: charged, enough free storage for 10 minutes plus margin, fixed mount per R-3, square-on, cluster in focus, bright regions not washed out (checked at the car with a test clip that is deleted or kept private).
- [ ] Rigid scale beside, not over, the cluster, only if Q8 is planned and a known pattern already exists.
- [ ] Second person present to record; operator and recorder have read the markers and stop conditions.
- [ ] Private destination available and not inside any Git work tree.
- [ ] Timer visible to the recorder.
- [ ] The agreed other page (F-3) is written down.

## 4. Recording sequence (one pass)

Recorder starts the recording, then says the marker aloud. The operator repeats each marker as the action begins. Times are relative to recording start.

| # | Marker | Action | Observe | Move on when |
|---|---|---|---|---|
| 1 | `BASELINE` | None. Casting off, factory Navigation. | Q1 | Steady for about 10 s. Operator says `CENTER_NORMAL`. |
| 2 | `CAST_ON` | Start casting through its familiar UI. | Q2 | Content visible, or 30 s with none (then go to step 8). |
| 3 | `GEOMETRY` (only if a known pattern is already shown) | None. Recorder holds a square-on view for about 10 s. | Q8 | 10 s elapsed. Otherwise skip and note `GEOMETRY_NOT_TESTED`. |
| 4 | `PAGE_AWAY` | Select the agreed other page with the normal control. | Q3, Q7 | New page steady about 5 s. **If cast content is visible: stop (stop condition) and go to step 8.** |
| 5 | `PAGE_BACK` | Select Navigation with the normal control. | Q4, Q7 | Steady about 5 s. |
| 6 | `CAST_OFF` | Press the normal Stop Casting control. | Q5 | About 10 s. |
| 7 | `RESTORED_CHECK` | None. Compare to step 1. Operator says `CENTER_NORMAL` or `CENTER_ABNORMAL`. | Q5, Q6, Q7 | About 10 s. |
| 8 | `END` | Stop recording within 60 s of step 7. | | |

Step 8 as an early exit: if casting is on, use only the normal Stop Casting control once, say `RESTORED_CHECK`, hold about 10 s, then `END`.

## 5. Stop conditions (immediate)

Any warning or interrupt appearing; unexpected prompt or UI; frozen or blank display; host restart; cast content visible on a non-Navigation page; camera obstruction or failure; elapsed time at 10:00; any uncertainty about the current page or casting state.

On a stop: say `STOP`; if casting is on, use the normal Stop Casting control once if it responds; hold the camera on the cluster about 10 s; end the recording. Do not dismiss or wait for a warning, retry, add a test, or run any diagnostic. The session is final for this approval.

## 6. After recording

- [ ] Verify casting is off and factory Navigation is visible; center display normal. If not, write down what is seen; **do not attempt a fix as part of this procedure** (the owner decides separately).
- [ ] Note anything unexpected in the private notes.
- [ ] Copy the original recording to the private session folder; seal it with the evidence tool; keep the original read-only.
- [ ] Do not upload the video anywhere. Do not stage anything in Git.

## 7. Off-vehicle rehearsal and camera preparation

Rehearse with a **dummy recording** (any harmless scene or a generated test clip). Never film Honda content for this. The rehearsal checks the workflow, not the vehicle.

| Check | How | Verified here |
|---|---|---|
| Record and play back | Record 60 s with the real camera; play it back. | **NOT_TESTED** (needs the camera; operator) |
| Small details resolvable | Film a printed chart with 2 mm and 4 mm text at the planned distance; text must be legible. | **NOT_TESTED** |
| Exposure of bright regions | Film a bright screen; highlights must keep detail. | **NOT_TESTED** |
| No unexpected stop | 12-minute dummy recording runs through. | **NOT_TESTED** |
| Markers correlate | Say markers while a visible timer runs; check offsets on playback. | **NOT_TESTED** |
| Transfer to private storage | Copy to the private folder; compare sizes. | Tool path verified with a synthetic clip |
| SHA-256 and manifest | `seal` then `verify`. | PASS with synthetic media |
| Raw vs redacted separation | Layout has separate directories. | PASS (layout and tests) |
| Raw not overwritten | `seal` refuses to overwrite its manifest; raw is read-only. | PASS (tests) |
| Raw cannot reach Git | Tool refuses a private root inside a work tree; the public-safety gate rejects media. | PASS (tests) |

Camera placement, focus, exposure and real-world conditions at the car are **PENDING** and are checked by the operator at the session. The rehearsal says nothing about them.

Commands (offline, no vehicle access; `ROOT` is the private session folder outside every repository):

```
python3 tools/cl_obs02_evidence.py init --root "$ROOT"
# copy the recording into "$ROOT/original-recording/", then:
python3 tools/cl_obs02_evidence.py seal --root "$ROOT" --raw "$ROOT/original-recording/<file>"
python3 tools/cl_obs02_evidence.py verify --root "$ROOT"
python3 tools/cl_obs02_evidence.py classify --root "$ROOT"
```

## 8. Approval packet

| Item | Content |
|---|---|
| Procedure to approve | Sections 3 to 6 of this packet at the reviewed PR head SHA, plus the PR #87 proposal at `fc4623f`. |
| Normal UI actions | Select Navigation, select the agreed page, start casting, Stop Casting, all via existing controls. |
| Equipment and personnel | One fixed camera, optional rigid scale, a visible timer; operator and recorder. |
| Time limit | One session, at most 10 minutes of recording. |
| Privacy | Raw media private only; sanitized table only; no VIN, phone id, GPS, account. |
| Stop and restoration | Sections 5 and 6; acceptance rules in the companion document. |
| Open reviewer items | R-1 center display in frame or by spoken marker; R-2 whether one pre-recording Stop Casting is allowed; R-3 camera mount. |
| Excluded | Section 9. |

Three signoffs are required, recorded privately against the PR head SHA reviewed:

1. Written owner authorization.
2. Independent qualified safety review. An AI review, including ECC, is not this.
3. Operator confirmation that they read the stop procedure.

Any missing item gives `VEHICLE_SESSION_NOT_AUTHORIZED`. Any edit to this packet after approval voids it.

## 9. Explicitly excluded

Honda ADB; live iPhone work; receiver changes; Xposed changes; APK install; private Binder calls; CAN interaction; firmware or system writes; framebuffer injection; warning induction; new content or patterns injected for geometry; route entry; CarPlay pairing; head-unit screenshots; any step not in section 4; repeat or exploratory runs; cloud upload.

## 10. Preparation status

- Documentation, evidence checklist, failure scenarios, tool and tests: complete in this PR.
- Camera placement at the vehicle: PENDING until the session.
- Optional geometry method: READY only if a known pattern is already displayed by the existing UI; otherwise `GEOMETRY_NOT_TESTED`.
- Exact plan independently reviewed: NO. Written owner approval: NO.
