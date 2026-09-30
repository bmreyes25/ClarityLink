# Step 42E — synthetic Type111 end-to-end replay

Date: 2026-09-30
Scope: offline simulation and tests only
Base: `c807600`

## Result

Implemented `synthetic_type111_cluster_replay` in two modes. `STRICT_HONDA` calls the stock Setup delegate first, retains its response and display information, and skips Type111. `HYPOTHETICAL_TYPE111` requires all capability-gate inputs, including the explicit unknown-field marker, and then runs a candidate-only path with generated synthetic values and an MHI2-derived response profile label.

The hypothetical replay allocates and accepts a fake listener, sends synthetic 128-byte ScreenStream headers with opcode 1 config and opcode 0 video, and runs them through the existing Type110-informed parser/config/H.264 extraction path. The extractor emits a synthetic Annex-B access unit. There is no H.264 decoder: a deterministic generated RGBA pattern frame follows successful extraction and is submitted to the Display 1 mock. The presentation timestamp and dimensions are synthetic; overlay policy and crop/mask remain unknown.

Type111-only teardown closes candidate listener/renderer resources and clears synthetic secret placeholders while the Type110 request/response snapshot, center display state, and synthetic audio snapshot remain unchanged. Full-session teardown is modeled separately and clears both streams, renderer, and audio state. The event timeline records stage order and evidence labels.

## Evidence boundary

- **HONDA_CONFIRMED:** recovered stock-first Setup ownership, Type110 response field shape, and unsupported Type111 skip behavior.
- **MHI2_DERIVED_HYPOTHESIS:** candidate cloned Type111 response profile and `streamID=111` profile behavior.
- **SYNTHETIC_TEST_VALUE:** generated ports, IDs, descriptor, cleartext packets, timestamps, audio state, and frame.
- **UNKNOWN:** Honda Type111 response schema, feature-generation requirements, display/stream correlation, Type111 key derivation/master reuse/opcode semantics, and physical ExternalDisplay composition.

The Type110 response is modeled as `{type: 110, dataPort: ...}`. The synthetic `streamConnectionID` remains on the Setup request; tests assert that it is neither changed there nor inserted into the stock Type110 response. No real key or proprietary packet fixture is used. This replay demonstrates model composition, not Honda or iPhone compatibility.

## Verification

- Negotiation: 18 passed.
- Transport/parser/H.264: 29 passed.
- Display/session: 12 passed.
- Renderer: 8 passed.
- New replay: 5 passed.
- Existing interposer tests: 14 passed through a standard-library assertion runner because pytest is unavailable in this environment.
- Host-only Display B integration smoke: passed.
- Simulator Python: 31 passed, 6 skipped because optional OpenCV/NumPy are unavailable.
- Simulator JavaScript suite: all seven scripts passed.
- Failure-injected twin: passed.
- `git diff --check`: passed.

## Decision gate

END-TO-END REPLAY: IMPLEMENTED
CAPABILITY GATING: IMPLEMENTED
STRICT HONDA MODE: PASS
HYPOTHETICAL TYPE111 MODE: PASS
TYPE110 PRESERVATION: PASS
TYPE111 SETUP MODEL: PASS
SCREENSTREAM REPLAY: PASS
VIDEO HANDOFF: SYNTHETIC_FRAME_SOURCE
RENDERER SUBMISSION: PASS
INDEPENDENT TEARDOWN: PASS
AUDIO INVARIANTS: PASS
EVIDENCE TAGGING: PASS
EVENT TIMELINE: IMPLEMENTED
SYNTHETIC TYPE111 DEMO: READY
OFFLINE DIGITAL TWIN: READY
JMCS NO-OP TEST: NOT READY
EXTERNALDISPLAY LIVE RENDER TEST: NOT READY
TYPE111 LIVE WORK: NOT READY
LD_PRELOAD STATUS: PARKED
BIGGEST BLOCKER: Honda Type111 response/security/display-correlation contract remains unknown, and no jmcs integration or supported ExternalDisplay frame handoff is available.

## Next

Build a visual offline cluster-demo view on top of the replay report, showing stock center Type110 and the generated Display 1 frame together while keeping evidence tags and unknowns visible. Keep all live gates closed.
