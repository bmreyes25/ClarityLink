# CL-OBS-02 evidence acceptance

**Evidence rules only. This document does not authorize a vehicle session.** Procedure: [preflight packet](cl-obs-02-preflight-packet.md). `safeForHonda() == false`.

An observation checklist is not an observation result. Nothing here claims that a car session took place.

## 1. Private layout

Keep this outside every Git work tree, in the owner's approved private storage. The tool refuses a root inside a work tree.

```
CL-OBS-02/<session id>/
  original-recording/         raw video, sealed, read-only
  integrity-manifest/         raw-sha256.json
  private-observation-notes/  manifest.json, observation.json, free notes
  redacted-analysis/          frames or clips after privacy review
  sanitized-public-summary/   text only, the sole candidate for publication
```

Do not put real paths or sensitive file names in public text. Do not require a VIN, phone identifier, GPS, or account name. Raw hashes are not published unless a public conclusion needs them.

### Evidence manifest (`manifest.json`)

Session id; session date; operator and recorder roles; recording format and duration; raw SHA-256; camera characteristics relevant to interpretation (resolution, frame rate, fixed mount, exposure and focus notes); event markers with relative times; completed or stopped; reason for any missing evidence; restoration result; privacy and redaction status. The tool writes a template with these fields.

## 2. Observation record (`observation.json`)

All fields are required. The classifier rejects a missing or out-of-range value rather than guessing.

| Field | Question | Allowed values |
|---|---|---|
| `baseline_recorded` | Q1 | step values |
| `casting_on_navigation` | Q2 | step values |
| `page_exit_result` | Q3 | step values |
| `page_reentry_result` | Q4 | step values |
| `stop_casting_result` | Q5 | step values |
| `center_display_normal` | Q6 | step values (operator's spoken marker; lower confidence) |
| `restoration_result` | Q5, Q7 | `RESTORED_ON_RECORDING`, `RESTORED_DIRECT_SIGHT_ONLY`, `NOT_RESTORED_OBSERVED`, `NOT_REACHED`, `NOT_CASTING_STARTED` |
| `stale_crop_overlap_anomaly` | Q7 | `NONE_SEEN`, `ANOMALY_SEEN`, `UNOBSERVABLE` |
| `geometry` | Q8 | `MEASURED_SAMPLE`, `GEOMETRY_NOT_TESTED`, `UNOBSERVABLE` |
| `session_status` | | `COMPLETED`, `STOPPED_EARLY` |
| `stop_reason` | | `NONE`, `WARNING_OR_PROMPT`, `CASTING_ON_OTHER_PAGE`, `DISPLAY_FROZEN_OR_BLANK`, `HOST_RESTART`, `CAMERA_FAILURE`, `TIME_LIMIT`, `OPERATOR_UNCERTAINTY`, `UNEXPECTED_UI` |
| `recording_duration_s` | | number, at most 600 |
| `recording_legible`, `event_timeline_preserved`, `integrity_manifest_created` | | true / false |
| `owner_written_approval`, `independent_safety_review`, `operator_read_stop_procedure` | | true / false |

Step values: `OBSERVED`, `NOT_OBSERVED`, `UNOBSERVABLE`, `NOT_REACHED`, `NOT_TESTED`. Mapping to per-item labels: `OBSERVED` is OBSERVED; `NOT_OBSERVED` and `UNOBSERVABLE` are INCONCLUSIVE for that item; `NOT_REACHED` follows an ABORTED stop; `NOT_TESTED` is NOT_TESTED. A result such as "cast content stayed visible off Navigation" is an OBSERVED finding recorded in the notes, not a missing observation.

`geometry = GEOMETRY_NOT_TESTED` never lowers the session class. A camera-derived rectangle is never called an OEM-authoritative or CarPlay SafeArea.

## 3. Session classes

Evaluated in this order; the first match wins.

| Order | Class | Rule |
|---|---|---|
| 1 | `VEHICLE_SESSION_NOT_AUTHORIZED` | Any of owner approval, independent safety review, or operator stop-procedure confirmation is missing. Not a session outcome: no evidence from such a session is valid. |
| 2 | `RESTORATION_UNVERIFIED` | Casting was started and restoration is not shown `RESTORED_ON_RECORDING` (not reached, seen only directly, visibly not restored, or the recording is missing, corrupt or fails its SHA-256 check). Takes priority over ABORTED and PARTIAL because restoration is the safety-relevant fact. |
| 3 | `INCONCLUSIVE` | Casting never started and the raw recording is missing or fails its digest. |
| 4 | `ABORTED` | The session stopped early (`STOPPED_EARLY` or a stop reason) and restoration needs no further proof (casting not started, or restored on recording). Evidence up to the stop may be useful; the session is not complete. |
| 5 | `INCONCLUSIVE` | Baseline missing, recording not legible, or no event timeline. |
| 6 | `PARTIAL_EVIDENCE` | Cast on Navigation observed, restoration on recording, but some planned items were unobserved, not reached, or the 10-minute limit was exceeded (protocol deviation). |
| 7 | `COMPLETE_EVIDENCE` | Every step field is `OBSERVED`, restoration on recording, timeline preserved, integrity manifest created, status `COMPLETED`, no stop reason, duration within 600 s. |
| 8 | `INCONCLUSIVE` | Anything else. |

A `COMPLETE_EVIDENCE` session may still contain anomalies; recording an anomaly is a result, not a failure of the session.

## 4. Failure scenarios (handled off the vehicle)

"Start?" is whether the session may begin or continue. No scenario is ever induced on the vehicle.

| Scenario | Start / continue? | Evidence kept | Class or item label | Must not claim | New authorization? |
|---|---|---|---|---|---|
| Camera battery failure | Before start: no, `NOT_TESTED`. During: stop. | Footage up to failure | `ABORTED` (casting not started) or `RESTORATION_UNVERIFIED` | Restoration or later steps | Yes, new session |
| Storage exhausted | As above | Footage up to the end | As above | As above | Yes |
| Out of focus | Before start: do not start until fixed; fixing the camera is allowed. After: not legible. | Raw file | `INCONCLUSIVE`, or `RESTORATION_UNVERIFIED` if casting started | Any visual conclusion | Yes if it ran |
| Missing event markers | Continue only if cues remain clear; otherwise stop | Raw file, clock times | `INCONCLUSIVE` | Timing or order of events | Yes |
| Corrupt or unreadable recording | n/a (found afterwards) | Operator notes only | `INCONCLUSIVE`, or `RESTORATION_UNVERIFIED` if casting started | Anything visual | Yes |
| Incomplete baseline | Do not proceed to casting | Baseline footage | `INCONCLUSIVE`; `NOT_TESTED` if never reached | Q2 to Q7 | Yes |
| Missing restoration footage | n/a | Everything before it | `RESTORATION_UNVERIFIED` | That factory Navigation returned | Yes |
| Geometry pattern not available | Continue without Q8 | Everything else | `GEOMETRY_NOT_TESTED`, no class change | Any aperture or SafeArea | Only to attempt Q8 later |
| Test stopped early | Stop | Footage up to the stop | `ABORTED` | Steps not reached | Yes to resume |
| Unexpected warning | Stop immediately | Footage including the warning | `ABORTED`, or `RESTORATION_UNVERIFIED` if casting active | Warning behavior in general | Yes |
| Casting visible on another page | Stop immediately, Stop Casting once | The transition footage | `ABORTED` with the finding recorded; `RESTORATION_UNVERIFIED` if not restored | Re-entry or stop behavior | Yes |
| Factory content not restored | End the session; no second attempt | Full footage | `RESTORATION_UNVERIFIED` | Any recovery guarantee | Yes, and a reviewed recovery plan |
| No owner authorization or no independent review | Do not start | None | `VEHICLE_SESSION_NOT_AUTHORIZED` | That a session is approved | Yes |

## 5. Public findings

Only a manually written, de-identified, text summary may be published, after review, from `sanitized-public-summary/`. Raw video, frames, the manifest, and raw digests stay private. Findings must carry the evidence label from [evidence classification](evidence-classification.md): `HONDA_CONFIRMED` observed runtime behavior, scoped to this one session, vehicle state and feature, and kept distinct from static findings. Casting and page selection are normal UI actions, so do not describe the session as read-only.

A successful observation still does not establish a supported admission path, OEM approval, general warning priority, host crash recovery, or a SafeArea.

## 6. Integrity checks

1. Hash the raw file immediately after copying it, with `seal`.
2. `verify` before any analysis and again before any publication.
3. Analysis works on copies in `redacted-analysis/`. The sealed original is read-only and the tool refuses to overwrite an existing manifest.
4. Before publishing, run the repository public-safety gate; it rejects media files and the candidate must contain only text.
