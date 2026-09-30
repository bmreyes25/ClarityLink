# Step 42D — failure-injected Type111 digital twin

**Scope:** synthetic offline simulation and tests only. No vehicle, ADB, Honda binary, boot/partition image, preload, live hook, real key, CAN, or proprietary payload fixture was used.

## Implementation

Added src/claritylink-sim/type111-failure-twin.js and tests/sim/test_type111_failure_twin.js. The model holds separate Type110, Type111, audio, session and event state. It snapshots stock response, active Type110 token/crypto counter, session status and synthetic audio fields before candidate failures, then asserts exact equality afterward. Type111 uses generated identifiers/ports and synthetic-hypothesis evidence labels; no key or IV bytes are represented.

The Type111-only path models setup, listener start, connection, header, VideoConfig, frame, renderer submit, disconnect and new generation. Injected errors close candidate Type111 resources only. Parent Type110 stream loss tears down its child Type111 stream; full-session disconnect clears both streams and audio. Type110-only stream disconnect retaining the synthetic audio state is a model policy, not a Honda fact.

The event timeline is an in-memory sequence of semantic names and injected failure stages. It does not retain request/media data and does not claim Honda emits matching events.

## Failure matrix and results

The complete matrix is in research/simulator/type111-failure-matrix.md. Tested groups:

- Negotiation: missing descriptor/correlation/response, unsupported skip, malformed request, missing/invalid ID, duplicate, request before Type110/session, and invalid port.
- Listener: allocation, bind/listen, accept timeout, teardown while accepting, disconnect before header and mid-header, reconnect.
- Security/transport: derivation unavailable, bad IV, missing CTR, config before key-ready, synthetic decrypt failure, opcode before config, malformed 128-byte header, oversized body and unknown opcode.
- Video: missing/malformed VideoConfig, unsupported NAL length, truncated SPS/PPS and AVCC, extractor failure.
- Renderer: unavailable, bad dimensions, timeout, missing ExternalDisplay host, unknown crop/mask and dropped frame.
- Session: Type111-only disconnect, Type110 parent disconnect, full disconnect and reconnect.

Across Type111 failures, Type110's stock response, active flag, synthetic stream token, crypto counter and the synthetic audio state remain unchanged. Type111 state returns to idle and may establish a fresh generation after disconnect. Parent/full-session teardown is the explicit exception that ends the relevant parent state.

## Audio and evidence limits

Audio state is classified SYNTHETIC_INVARIANT, not Honda-confirmed. It contains only symbolic center-active, voice-route-active and focus-owner fields. Type111 failure cannot mutate these; full CarPlay disconnect clears them. Detailed Honda focus ownership and Type110-only audio coupling remain unknown.

Honda Type110 framing/opcode/config observations inform parser boundaries only. The test does not assert Honda uses these for Type111. Type111 response fields and display correlation remain unknown; no defaults fill those gaps. MHI2-inspired protocol fields remain hypothesis-labeled.

## Readiness gate

FAILURE MATRIX: DEFINED
AUDIO STATE MODEL: SYNTHETIC_INVARIANT
TYPE110 ISOLATION TESTS: PASS
TYPE111 FAILURE TESTS: PASS
CRYPTO ISOLATION TESTS: PASS
RENDERER FAILURE TESTS: PASS
SESSION TEARDOWN TESTS: PASS
EVENT TIMELINE: IMPLEMENTED
OFFLINE DIGITAL TWIN: ROBUST
SYNTHETIC TYPE111 DEMO: READY
JMCS NO-OP TEST: NOT READY
EXTERNALDISPLAY RENDER TEST: NOT READY
TYPE111 LIVE WORK: NOT READY
LD_PRELOAD STATUS: PARKED
BIGGEST BLOCKER: no proven jmcs entry or ExternalDisplay frame handoff; Honda Type111 wire/security/correlation are also unresolved

“Robust” applies to the modeled synthetic lifecycle/failure surface, not real Honda or iPhone compatibility.
