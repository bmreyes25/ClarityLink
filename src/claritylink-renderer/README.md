# ClarityLink renderer prototype

This offline prototype separates:

- FrameSource: emits synthetic or future decoded frames.
- ClarityLinkRenderer: validates target/frame metadata and owns lifecycle.
- Display1OutputBackend: accepts frames for an output target; the current host backend is a mock.

The synthetic source creates 800×480 RGBA_8888 frames with a border, grid, frame counter/timestamp, moving rectangle, and “CLARITYLINK DISPLAY 1” label. Its RGBA row stride is explicit and is unrelated to the vehicle framebuffer stride.

The API 17 Java skeleton uses an Android View supplied by a Host adapter to Honda's ExternalDisplay main layer. It does not acquire that private root, select a physical crop, perform zero-copy decoding, or claim hardware output. These integrations remain TODOs. It converts RGBA components to Android ARGB pixels explicitly because the fbdev/HWC storage format is not established.

The R4B `turn_cards.py` module is a separate **host-only** route-card state model. It reads synthetic/manual data, reserves nonoverlapping 800×480 layout regions, clears stale guidance, and returns a JSON-ready card. It never calls the frame backend or Android adapter. See [R4B requirements](../../research/runtime/43t1-r4b-turn-card-renderer-requirements.md). Run `python3 tools/r4b_preview.py` from the repository root for synthetic JSON snapshots.

Run the host unit tests from the repository root:

    python3 -m unittest discover -s src/claritylink-renderer/tests -v

## Synthetic structured navigation (API 17)

`NavigationUpdate` is a plain-Java semantic contract carrying session, generation,
sequence, maneuver, distance/unit, and a road name bounded to 256 characters.
`StructuredNavigationSink` and `StructuredNavigationOutputBackend` accept this type on a separate path from
`DecodedFrame`; it attaches only to a caller-supplied synthetic host. A
`NavigationGenerationLedger` must be retained by the caller across host recreation
so a replacement host cannot reuse an old generation. Warning interruption and
host loss clear guidance synchronously. Resuming a host never restores old guidance;
the caller must explicitly begin a newer generation. The generic view is a test
fixture and does not establish factory warning precedence or authorize factory
output. `safeForHonda()` remains false.

The focused Java contract is `android/src/test/java/org/claritylink/renderer/NavigationUpdateTest.java`.
`android/cl-imp-03-app/java/org/claritylink/android/StructuredNavigationLabActivity.java`
drives the lifecycle scenario on the API 17 emulator and emits a machine-readable
runtime marker.

## Simulated Navigation pane leases (API 17)

`Display1OutputBackend` obtains a single-use `PaneLease` from its caller-owned
simulator host. Page exit, interrupt activation, host loss, a host viewport-change event, or
close revokes the lease, detaches the View, and clears queued frame work.
Selection, interrupt clear, and host restoration never restore old authority;
recovery requires an explicit attach with a higher pane generation. Frame
submission reports typed runtime rejection while programmer contract errors
continue to throw. Only the existing synthetic-test viewport contract is
accepted. Accepted Type111 ViewArea/SafeArea geometry is applied in place with
`setRendererViewport` while the lease is valid and never revokes it. This is simulator-only renderer behavior; it does not identify a
physical Navigation aperture, authorize a Honda host, or change either Honda
feasibility gate. `safeForHonda()` remains false.
