# CL-OBS-02 camera rehearsal and private storage

**Off-vehicle preparation. Not an observation, not an authorization.** Never film or access the Honda, its displays or any vehicle content for this. `safeForHonda() == false`. Companion to the [operator packet](cl-obs-02-operator-packet.md) and the [evidence acceptance rules](cl-obs-02-evidence-acceptance.md).

## Status

| Item | Status |
|---|---|
| Synthetic media through the tool (seal, verify, classify) | PASS (automated tests, dummy bytes) |
| Real-camera rehearsal with the actual camera | **PENDING** (no real-camera footage has been tested; the steps below are for the operator) |
| Private storage layout exists and passes the tool's checks | PASS (checked offline, see below) |
| Private storage location approved by the owner | **PENDING** |

## 1. Real-camera rehearsal (operator, at home, nothing from the vehicle)

Use the camera, memory card, battery or power source, and support intended for the session. Subject: a harmless scene, such as a printed test chart and a screen showing a visible running timer. The rehearsal may run longer than the 10-minute vehicle limit to prove endurance; that does not make it an observation.

| # | Check | Pass when |
|---|---|---|
| 1 | Resolution and frame rate | Settings recorded in the private notes; printed text of the planned smallest size (2 mm and 4 mm at the planned distance) is legible on playback |
| 2 | Focus | Stays sharp for the whole clip; autofocus does not hunt when a hand moves in front |
| 3 | Exposure | A bright screen keeps detail; a lit screen beside a dark surround stays readable in both regions |
| 4 | Storage | Free space shown for at least 10 minutes plus 50 percent margin at the chosen quality |
| 5 | Battery or power | A 12-minute continuous clip finishes with margin, using the same power setup planned for the session |
| 6 | Audio markers | Speak each marker (`BASELINE`, `CAST_ON`, `PAGE_AWAY`, `PAGE_BACK`, `CAST_OFF`, `RESTORED_CHECK`, `CENTER_NORMAL`, `END`, `STOP`) next to the visible timer; on playback each is audible and its offset can be read |
| 7 | Stable positioning | Camera on the planned support does not drift or vibrate; frame unchanged start to end |
| 8 | Continuity | No automatic file split, sleep or stop; one file for the whole clip |
| 9 | Playback | The file plays in a standard player without repair |
| 10 | Private transfer | Copy to the private folder over a local cable or card reader, not a cloud or sync service; sizes match |
| 11 | Seal and verify | Commands below print `VERIFIED: match` |
| 12 | Tamper detection | On a **copy**, change one byte; `verify` must print `FAILED: digest mismatch` |

If the camera splits long recordings into several files, choose settings that avoid it, because the tool seals exactly one file per session.

### Rehearsal commands

```
ROOT=<rehearsal folder outside every repository, with a dummy session name>
python3 tools/cl_obs02_evidence.py init   --root "$ROOT"
# copy the rehearsal clip into "$ROOT/original-recording/", then:
python3 tools/cl_obs02_evidence.py seal   --root "$ROOT" --raw "$ROOT/original-recording/<file>"
python3 tools/cl_obs02_evidence.py verify --root "$ROOT"
```

Use a separate rehearsal root. Never seal a rehearsal clip in the real session folder. Record the outcome (pass or fail per row, camera model class, settings) privately. Do not upload the clip. Real-camera testing counts as passed only when these rows were actually run with the real camera.

## 2. Private storage procedure

1. Choose the private session folder outside every Git work tree, on a local volume that supports hard links (APFS), and write the choice into the owner authorization.
2. Restrict the folder to the owner (mode 700 on the session folder and its parent is recommended; the tool sets 700 only on folders it creates).
3. `init` creates the five subfolders and a metadata template. It is safe to run on an existing folder: existing files are kept, and it refuses a Git work tree, a symlinked subfolder or a symlinked template.
4. Never delete or reinitialize evidence. Never reuse a session folder for a second session.
5. Keep the original recording sealed and read-only. Work only on copies in `redacted-analysis/`. Run `verify` before analysis and before any publication.
6. Only a manually written, de-identified text summary from `sanitized-public-summary/` may leave the private folder, after review.

### Check of the existing private layout (offline, no changes made)

The previously prepared private folder was checked read-only on this Mac by the preparing assistant (an operator-reported note, not independently reproducible from the repository; the owner should re-run `verify` and look at the folder). It exists; it is outside every Git work tree (the tool's check passes for the root and every subfolder); the five subfolders are owner-only; there are no symlinks; it holds only the metadata template; `verify` correctly reports no integrity manifest yet; `seal` rejects a missing file. Its parent folder is not owner-only, which is why step 2 recommends restricting it. Nothing was written, deleted or reinitialized.

This is a programmatic check only. **It is not the owner's approval of that location.** Storage approval stays PENDING until the owner records it in the authorization.

### Independent check of an original recording

Without this tool: `shasum -a 256 "$ROOT/original-recording/<file>"` must equal the `sha256` field in `$ROOT/integrity-manifest/raw-sha256.json`, and `stat` must report the same byte count.
