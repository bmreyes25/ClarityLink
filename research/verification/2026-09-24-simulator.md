# Simulator verification — 2026-09-24

**Scope:** Mac-only changes under `clarity-analysis/research`. No vehicle command, install, receiver binary patch, or original-backup write was performed. The pristine backup directory still reports `dr-x------`.

## Build and source checks

- `python3 research/simulator/build_simulator_assets.py` generated the display profile and local sample bundle from working copies and JSONL logs.
- `python3 -m py_compile` passed for the changed Python files.
- `node --check` passed for `digital-twin.js` and `samples.js`; `display-profile.json` parsed as JSON.
- The copied `j_config.xml` and `meter_civic.xml` hashes match their extracted sources. Copied screenshot hashes match the read-only capture, and each PNG is 800×480.

## Tests

| Command | Result | Guarantee |
|---|---|---|
| `python3 -m unittest discover -s research/simulator -p 'test_*.py'` | 4 passed | Source-copy/profile integrity; saved OCR produces only a planned visual broadcast; unknown text produces no turn; OCR has finite timeout. |
| `node research/simulator/test-capture-replay.js` | Passed | Captured frame IDs are restricted by display; synthetic guidance clears before Music; disconnect clears frames. |
| `node research/simulator/test-dual-screen.js` | Passed | The independent-stream *model* handles center app changes and teardown. |
| `node research/contracts/validate-cluster-stream.js` and `test-cluster-stream.js` | Passed | Contract fixture and seven invalid lifecycle paths. |

The captured replay test initially failed on an unknown event type before `capture-frame` support was added. The profile test initially failed because no generated profile existed. The bridge timeout test initially failed because the OCR subprocess had no timeout; it now uses 45 seconds. Coverage percentage was not measured; these tests exercise the changed behavior and key failure paths, not the entire legacy bridge.

## Browser inspection

In the local browser, **Load captured displays** showed center Music next to the saved Honda compass HDMI frame at event 7 of 8. The 584×215 proposed guidance preview had cleared by that point. Event 8 cleared both screenshots and all guidance. The browser tab was kept open as a deliverable.

## Security and limits

A focused scan of changed source/config files found no credentials or private keys. The saved PNGs may reveal route and music details and remain local. The simulator cannot prove a second iPhone video stream, physical cluster safe area, sustained H.264 decoding, or audio behavior after a future patch. The two HDMI screenshots from the parked session were byte-identical; that observation is limited to that capture.
