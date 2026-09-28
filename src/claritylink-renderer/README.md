# ClarityLink renderer prototype

This offline prototype separates:

- FrameSource: emits synthetic or future decoded frames.
- ClarityLinkRenderer: validates target/frame metadata and owns lifecycle.
- Display1OutputBackend: accepts frames for an output target; the current host backend is a mock.

The synthetic source creates 800×480 RGBA_8888 frames with a border, grid, frame counter/timestamp, moving rectangle, and “CLARITYLINK DISPLAY 1” label. Its RGBA row stride is explicit and is unrelated to the vehicle framebuffer stride.

The API 17 Java skeleton uses an Android View supplied by a Host adapter to Honda's ExternalDisplay main layer. It does not acquire that private root, select a physical crop, perform zero-copy decoding, or claim hardware output. These integrations remain TODOs. It converts RGBA components to Android ARGB pixels explicitly because the fbdev/HWC storage format is not established.

Run the host unit tests from the repository root:

    python3 -m unittest discover -s src/claritylink-renderer/tests -v
