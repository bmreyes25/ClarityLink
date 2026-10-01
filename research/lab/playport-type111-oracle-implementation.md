# PlayPort Type111 oracle lab implementation

**Step 43O status: offline implementation complete; no iPhone session performed.** The isolated checkout is `../playport-type111-lab`, branch `claritylink-type111-lab`, based on PlayPort `9a0882dd0ffe48e467b59d58b12d81391df55ade`, with local lab commit `57df00125f2aedde5c2ab1a3d6e3295e242cd6f3`. It is not vendored into ClarityLink and has no upstream push.

## Lab features

- PlayPort's existing `AirPlayConfig.cluster` is enabled only by `--cluster`. Without that flag, cluster remains `null`, retaining the pinned main-only protocol profile.
- The lab profile defaults to 800×480 at 30 fps, with no physical dimensions and `maps:/car/instrumentcluster/map`. These are synthetic values, not Honda geometry or Honda protocol facts.
- Optional width, height, fps, physical dimensions, and URL flags configure only the second display.
- Browser canvases, `VideoPlayer`/WebCodecs decoder state, codec configuration, frame readiness, recovery requests, and HUD counters are keyed separately for 110 and 111. Type111 inactivity, decoder errors, teardown, or restart do not close or reset Type110.
- An alternate screen socket EOF now releases only its own media stream. The existing main-screen EOF behavior still closes its AirPlay session.
- Opt-in `--type111-diagnostics` emits JSON lines from an allowlist. `/info`, SETUP negotiation, stream setup, socket open, control, config/frame, and teardown metadata are represented. `streamConnectionID` contents are retained only for an in-memory equality comparison and are never logged; diagnostics report presence and whether it differs from the other screen ID.
- The protocol implementation labels its observed parser protection branch as `MODERN_CHACHA_SCREEN` or `CLEAR_OR_UNKNOWN`. This describes PlayPort's local parser branch, not Honda and not an independent proof of what a future iPhone negotiated. Honda Type111 security remains `HONDA_UNKNOWN`.

The diagnostics do not store request bodies, media payloads, MFi material, pairing secrets, authentication challenges/signatures, session keys, or derived keys. Unsupported fields are dropped by the centralized allowlist. The debug paths that formerly dumped decoded `/info`, SETUP stream, and TEARDOWN content now log keys/types only; the main screen key log records only whether a connection ID exists.

## Baseline and validation

The exact pinned baseline was built before edits. `:server:test` and `:protocol:test`, the full `./gradlew build`, `npm test`, and `npm run build` pass after edits. Gradle used the temporary `/tmp/cl-jdk25` runtime because the host had no Java runtime configured; no system Java was changed. The web test remains a Node synthetic DOM/input test plus structural assertions for separate stream canvases and routing. Kotlin tests cover opt-in defaults, field allowlisting, diagnostic opt-in, advertisement without a Type111 request, reversed stream order, independent start/stop/restart, controls, and failure isolation.

The protocol library's broader build tests also pass, including its existing 110/111 SETUP and `(session,type)` handling. This is not a real phone observation. The oracle has not established what current iOS requests, whether it opens the advertised port, or whether an actual Type111 stream succeeds.

## Readiness

`PLAYPORT TYPE111 LAB: READY_OFFLINE`; `DUAL 110/111 UI: READY_SYNTHETIC`; `REDACTED ORACLE: READY`; `LIVE IPHONE ORACLE: NOT RUN`. PlayPort implements a modern ChaCha screen path, so an AES-era peer may not be compatible. No Honda crypto or runtime behavior has been tested. Step 43P remains the separately scoped Mac/iPhone observation; Step 43Q remains conditional on reviewing that trace.
