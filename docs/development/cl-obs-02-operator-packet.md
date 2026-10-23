# CL-OBS-02 operator packet

**Do not use in a vehicle until signoff status below reads APPROVED for this exact revision.** This is a condensed checklist of the [preflight packet](cl-obs-02-preflight-packet.md) (sections 3 to 6) and the PR #87 proposal at `fc4623f9e0b7798f9f3f335f2ca4d5d448bdc799`. If anything here disagrees with them, stop and ask; the stricter text governs. `safeForHonda() == false`.

One parked session. One pass. At most 10 minutes of recording. **Nothing else: no ADB, phone work, installs, settings changes, warnings, retries or repairs.**

## Signoff status (filled in privately; this public copy stays PENDING)

Owner authorization: PENDING. Independent safety review: PENDING. Operator stop-procedure acknowledgment: PENDING. Camera mount (R-3): PENDING. Center display framing (R-1): PENDING. Pre-recording Stop Casting (R-2): PENDING (default: not allowed). Storage approval: PENDING. Real-camera rehearsal: PENDING.

## Before recording (any failed item = do not start, record `NOT_TESTED`)

- [ ] All signoffs above APPROVED for this PR head SHA.
- [ ] Parked, parking brake on; vehicle state is the one the owner normally uses for casting.
- [ ] Casting is **off**; factory Navigation shown; center display normal; no warning or unexpected prompt.
- [ ] Agreed other factory page written down: ______
- [ ] Camera charged, free storage for 10 min plus margin, in focus, bright areas not washed out.
- [ ] Camera placement as approved (see below). Timer visible to the recorder.
- [ ] Operator and recorder have read the markers and the stop conditions.
- [ ] Private destination chosen, outside every Git work tree.

## Camera placement

- Camera and support must not block the driver's view of the road, gauges, warnings or controls.
- Nothing attached to or touching the instrument cluster, steering wheel, steering column controls or airbag cover. Do not move the steering wheel during the session.
- Cluster fully in frame, sharp, stable. Do not touch or modify the cluster.
- Center display is **not** in the frame unless the reviewer decided so (R-1). If not, the operator's spoken `CENTER_NORMAL` or `CENTER_ABNORMAL` is the only evidence: operator attestation, lower confidence than video.

## Markers (speak aloud; operator repeats as each action starts)

`BASELINE`, `CAST_ON`, `GEOMETRY` (only if a known pattern is already shown), `PAGE_AWAY`, `PAGE_BACK`, `CAST_OFF`, `RESTORED_CHECK`, `CENTER_NORMAL` / `CENTER_ABNORMAL`, `END`, `STOP`.

## Sequence

1. Recorder starts recording and timer. `BASELINE`: hold about 10 s. Operator says `CENTER_NORMAL`.
2. `CAST_ON`: start casting with the familiar UI. Content visible, or 30 s with none, then go to step 7.
3. `PAGE_AWAY`: select the agreed other page with the normal control. Hold about 5 s. **If cast content is still visible: that is a stop condition; go to step 7.**
4. `PAGE_BACK`: select Navigation with the normal control. Hold about 5 s.
5. `CAST_OFF`: press the normal Stop Casting control once. Hold about 10 s.
6. `RESTORED_CHECK`: compare with the baseline; operator says `CENTER_NORMAL` or `CENTER_ABNORMAL`. Hold about 10 s.
7. `END`: if casting is still on, press the normal Stop Casting control once, say `RESTORED_CHECK`, hold about 10 s. Stop the recording within 60 s.

At 8:00 skip to Stop Casting. At 10:00 stop recording regardless.

## Stop conditions (immediate)

Any warning or interrupt; unexpected prompt or UI; frozen or blank display; host restart; cast content on a non-Navigation page; camera obstruction or failure; 10:00; any doubt about the current page or casting state.

Say `STOP`. If casting is on and Stop Casting responds, press it once. Hold the camera on the cluster about 10 s. End the recording. Do **not** dismiss or wait for a warning, retry, toggle, fix, or run anything. The approval is used up.

## Restoration checks

Restored means: casting off, factory Navigation looks like the baseline, center display normal. If it is not, write down exactly what is seen, end the session, and do not try to fix it. The owner decides any recovery separately.

## After the session

1. Copy the original recording into `ROOT/original-recording/` (private folder, outside Git). Do not edit, trim or convert it.
2. Seal and verify (commands below). Verify again before any analysis or publication.
3. Write `observation.json` honestly in `ROOT/private-observation-notes/`; set the three approval fields true only if the signed approvals exist.
4. Work only on copies in `redacted-analysis/`. Never upload video. Never stage anything in Git.
5. Delete the camera's copy only after the sealed original is verified and the owner's retention rule allows.

## Tool commands (offline, no vehicle)

```
ROOT=<private session folder outside every repository>
python3 tools/cl_obs02_evidence.py init     --root "$ROOT"
# copy the recording into "$ROOT/original-recording/", then:
python3 tools/cl_obs02_evidence.py seal     --root "$ROOT" --raw "$ROOT/original-recording/<file>"
python3 tools/cl_obs02_evidence.py verify   --root "$ROOT"
python3 tools/cl_obs02_evidence.py classify --root "$ROOT"
```

`verify` prints `VERIFIED: match` (exit 0) or `FAILED: <reason>` (exit 1). `classify` prints one class and reasons; exit 2 means the record is invalid or contradictory and must be corrected, not worked around.

## Failure classification (summary)

| Class | Meaning |
|---|---|
| `VEHICLE_SESSION_NOT_AUTHORIZED` | A required approval is missing; no evidence from that session is valid |
| `RESTORATION_FAILED_OBSERVED` | Casting started and factory content was seen **not** restored |
| `RESTORATION_UNVERIFIED` | Casting started and restoration was not shown on a verified recording (not reached, direct sight only, inconclusive, or recording unusable) |
| `ABORTED` | Stopped early; restoration needs no further proof |
| `INCONCLUSIVE` | Baseline, legibility, timeline or recording missing |
| `PARTIAL_EVIDENCE` | Some planned or mandatory observations unobserved, or time limit exceeded |
| `COMPLETE_EVIDENCE` | Every mandatory observation made and restoration shown on the recording |

Full definitions: [evidence acceptance](cl-obs-02-evidence-acceptance.md#3-session-classes).
