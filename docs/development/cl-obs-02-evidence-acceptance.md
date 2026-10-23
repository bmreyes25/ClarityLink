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
| `restoration_result` | Q5, Q7 | `RESTORED_ON_RECORDING`, `RESTORED_DIRECT_SIGHT_ONLY`, `NOT_RESTORED_OBSERVED`, `RESTORATION_INCONCLUSIVE`, `NOT_REACHED`, `NOT_CASTING_STARTED` (meanings in section 2.1) |
| `stale_crop_overlap_anomaly` | Q7 | `NONE_SEEN`, `ANOMALY_SEEN`, `UNOBSERVABLE` |
| `geometry` | Q8 | `MEASURED_SAMPLE`, `GEOMETRY_NOT_TESTED`, `UNOBSERVABLE` |
| `session_status` | | `COMPLETED`, `STOPPED_EARLY` |
| `stop_reason` | | `NONE`, `WARNING_OR_PROMPT`, `CASTING_ON_OTHER_PAGE`, `DISPLAY_FROZEN_OR_BLANK`, `HOST_RESTART`, `CAMERA_FAILURE`, `TIME_LIMIT`, `OPERATOR_UNCERTAINTY`, `UNEXPECTED_UI` |
| `recording_duration_s` | | finite number, 0 to 86400; above 600 is a protocol deviation (PARTIAL), 0 never completes |
| `recording_legible`, `event_timeline_preserved`, `integrity_manifest_created` | | true / false |
| `owner_written_approval`, `independent_safety_review`, `operator_read_stop_procedure` | | true / false |

Contradictory records are rejected, not classified. Unknown extra fields, wrong types, `NaN`/`Infinity`, and these combinations are validation errors:

- `casting_on_navigation` of `NOT_TESTED` or `NOT_REACHED` (casting never started) if and only if `restoration_result = NOT_CASTING_STARTED`; with casting not started, exit, re-entry and stop-casting cannot be `OBSERVED`.
- Casting counts as started for `OBSERVED`, `NOT_OBSERVED` and `UNOBSERVABLE`, so those with `restoration_result = NOT_REACHED` classify as `RESTORATION_UNVERIFIED`.
- `session_status = STOPPED_EARLY` if and only if `stop_reason` is not `NONE`.
- `RESTORED_ON_RECORDING` requires a legible recording and `OBSERVED` for both `stop_casting_result` and `center_display_normal`. Missing restoration evidence is never inferred as restored.

The tool also refuses a private root that is inside a Git work tree (the root is resolved through symlinks first; a pre-existing symlinked layout subdirectory is refused), or whose Git state cannot be determined (it fails closed). A malformed or path-bearing integrity manifest, a non-hex digest, a symlinked or non-directory `original-recording/` or `integrity-manifest/`, any extra file next to the sealed recording (only Finder's `.DS_Store` is ignored), or a raw recording with more than one hard link fails verification. `seal` refuses the same extra-file and hard-link conditions, so exactly one file is sealed per session. `seal` publishes the manifest atomically, never overwrites one, and removes only a manifest it created if sealing then fails (raw file cannot be made read-only, or it changed while sealing). It needs a filesystem with hard-link support (not exFAT); on one that lacks it, `seal` fails closed.

Step values: `OBSERVED`, `NOT_OBSERVED`, `UNOBSERVABLE`, `NOT_REACHED`, `NOT_TESTED`. Mapping to per-item labels: `OBSERVED` is OBSERVED; `NOT_OBSERVED` and `UNOBSERVABLE` are INCONCLUSIVE for that item; `NOT_REACHED` follows an ABORTED stop; `NOT_TESTED` is NOT_TESTED. A result such as "cast content stayed visible off Navigation" is an OBSERVED finding recorded in the notes, not a missing observation.

`geometry = GEOMETRY_NOT_TESTED` never lowers the session class. A camera-derived rectangle is never called an OEM-authoritative or CarPlay SafeArea.

### 2.1 Restoration values

| Value | Meaning | Class when casting started |
|---|---|---|
| `RESTORED_ON_RECORDING` | Restoration positively seen on a legible, verified recording | May reach `COMPLETE_EVIDENCE` |
| `RESTORED_DIRECT_SIGHT_ONLY` | Seen by a person but not on the recording | `RESTORATION_UNVERIFIED` |
| `NOT_RESTORED_OBSERVED` | Failure to restore **positively observed** (directly or on the recording) | `RESTORATION_FAILED_OBSERVED` |
| `RESTORATION_INCONCLUSIVE` | Restoration was checked but the view or footage cannot tell | `RESTORATION_UNVERIFIED` |
| `NOT_REACHED` | The session ended before restoration was checked | `RESTORATION_UNVERIFIED` |
| `NOT_CASTING_STARTED` | Casting never started, so there was nothing to restore | n/a (see the class table) |

`RESTORATION_FAILED_OBSERVED` is a known bad outcome; `RESTORATION_UNVERIFIED` is an unknown one. Neither is ever `COMPLETE_EVIDENCE`. The observed failure is also reported in the reasons when the session is unauthorized or the recording fails its digest. `NOT_RESTORED_OBSERVED` does not constrain `center_display_normal`: the cluster can stay unrestored while the center display is normal.

### 2.2 Mandatory and optional observations

Q1 to Q7 are mandatory for `COMPLETE_EVIDENCE`. `COMPLETE_EVIDENCE` means every mandatory observation was actually made and restoration was shown on the recording; it never implies that an unobservable condition was verified. Q7 (`stale_crop_overlap_anomaly`): `NONE_SEEN` and `ANOMALY_SEEN` are both answers (an anomaly is a result); `UNOBSERVABLE` is a gap and gives `PARTIAL_EVIDENCE`. Q8 (`geometry`) is optional: `GEOMETRY_NOT_TESTED` and `UNOBSERVABLE` never lower the class. No scenario may be induced to make a question observable.

## 3. Session classes

Evaluated in this order; the first match wins.

| Order | Class | Rule |
|---|---|---|
| 1 | `VEHICLE_SESSION_NOT_AUTHORIZED` | Any of owner approval, independent safety review, or operator stop-procedure confirmation is missing. Not a session outcome: no evidence from such a session is valid. |
| 2a | `RESTORATION_FAILED_OBSERVED` | Casting was started and `restoration_result = NOT_RESTORED_OBSERVED`, whatever the recording's integrity. A positively observed failure, not a missing observation. |
| 2b | `RESTORATION_UNVERIFIED` | Casting was started and restoration is not shown `RESTORED_ON_RECORDING` (not reached, seen only directly, inconclusive, or the recording is missing, corrupt or fails its SHA-256 check). Takes priority over ABORTED and PARTIAL because restoration is the safety-relevant fact. |
| 3 | `INCONCLUSIVE` | Casting never started and the raw recording is missing or fails its digest. |
| 4 | `ABORTED` | The session stopped early (`STOPPED_EARLY` or a stop reason) and restoration needs no further proof (casting not started, or restored on recording). Evidence up to the stop may be useful; the session is not complete. |
| 5 | `INCONCLUSIVE` | Baseline missing, recording not legible, or no event timeline. |
| 6 | `PARTIAL_EVIDENCE` | Cast on Navigation observed, restoration on recording, but some planned items were unobserved, not reached, Q7 was `UNOBSERVABLE`, or the 10-minute limit was exceeded (protocol deviation). With casting not observed the class is `INCONCLUSIVE` even over the time limit; the deviation is still listed in the reasons. |
| 7 | `COMPLETE_EVIDENCE` | Every step field is `OBSERVED`, Q7 is `NONE_SEEN` or `ANOMALY_SEEN`, restoration on recording, timeline preserved, integrity manifest created, status `COMPLETED`, no stop reason, duration within 600 s. |
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
| Casting visible on another page | Stop immediately, Stop Casting once | The transition footage | `ABORTED` with the finding recorded; `RESTORATION_FAILED_OBSERVED` if seen not restored, `RESTORATION_UNVERIFIED` if restoration was not shown | Re-entry or stop behavior | Yes |
| Factory content not restored | End the session; no second attempt | Full footage | `RESTORATION_FAILED_OBSERVED` | Any recovery guarantee | Yes, and a reviewed recovery plan |
| No owner authorization or no independent review | Do not start | None | `VEHICLE_SESSION_NOT_AUTHORIZED` | That a session is approved | Yes |

## 5. Public findings

Only a manually written, de-identified, text summary may be published, after review, from `sanitized-public-summary/`. Raw video, frames, the manifest, and raw digests stay private. Findings must carry the evidence label from [evidence classification](evidence-classification.md): `HONDA_CONFIRMED` observed runtime behavior, scoped to this one session, vehicle state and feature, and kept distinct from static findings. Casting and page selection are normal UI actions, so do not describe the session as read-only.

A successful observation still does not establish a supported admission path, OEM approval, general warning priority, host crash recovery, or a SafeArea.

## 6. Integrity checks

1. Hash the raw file immediately after copying it, with `seal`.
2. `verify` before any analysis and again before any publication.
3. Analysis works on copies in `redacted-analysis/`. The sealed original is read-only and the tool refuses to overwrite an existing manifest.
4. Before publishing, run the repository public-safety gate; it rejects media files and the candidate must contain only text.

## 7. Residual risks and assumptions

Threat model: accidental misuse and ordinary evidence integrity by the owner on their own Mac. The system is **not tamper-proof** and does not claim to be.

| Residual risk | Why accepted | Mitigation |
|---|---|---|
| A local attacker or another process running as the same user can swap or edit files between a check and its use (TOCTOU), including during `seal`, or can `chmod` the read-only original | Defending against a same-user adversary needs an OS-level model out of scope here | The post-publish re-hash in `seal`, `verify` before analysis and again before publication, read-only modes as a guard against accidents |
| Hard links created outside the tool | Detected at `seal` and `verify` through the link count, but a link made later in a place the tool never looks cannot be ruled out | `verify` re-checks the link count; keep the private folder on a single local volume |
| The manifest and the recording live in the same private root, so someone who can edit both can make them agree | Integrity here detects accidents and corruption, not forgery | Optionally keep an offline copy of the digest (a handwritten note or a separate private location) |
| No `O_NOFOLLOW`-style opens for hashing | Paths are checked immediately before use under the threat model above | Symlinked layout directories and manifests are rejected |
| `seal` prints the file name and digest to the terminal | Useful for the owner's own notes | Keep terminal logs private; never paste them into public text |
| Read-only modes are set at `seal` and not re-checked by `verify`; the digest, not the mode, is the integrity check | Modes guard against accidents only | Rely on `verify`; treat a writable raw file as a reason to re-verify |
| An interrupt (signal) between publishing the manifest and recording that fact in `seal` can leave an orphan manifest | Fails closed: a retry refuses to overwrite it. Cleaning it up is a manual owner step | Remove only that manifest, then re-run `seal` after confirming the raw file is unchanged |
| The three approval fields in `observation.json` are self-attested booleans | The tool cannot verify signatures | A `COMPLETE_EVIDENCE` label is only as trustworthy as the private record; set them true only with the signed approvals |
| `classify` exits 0 for every class | The class is the output; exit 2 means an invalid record | Read the first output line, do not rely on the exit code to detect a bad outcome |
| A filesystem without hard-link support (exFAT) | `seal` fails closed | Use an APFS or similar private volume |

Camera video proves only what the camera saw. Center-display state recorded from a spoken marker is operator attestation, not independently verifiable evidence.
