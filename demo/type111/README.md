# Synthetic Type111 visual demo

This static page visualizes the Step 42E digital-twin replay. It uses only Python's standard library to produce the JSON summary and a local browser to display it. It makes no network requests beyond the local HTTP server and contains no Honda captures, keys, or firmware assets.

From the repository root, generate the data and start the local server:

```sh
python3 src/claritylink-sim/export_visual_demo.py
python3 -m http.server 8000 --bind 127.0.0.1 --directory demo/type111
```

Open `http://localhost:8000` in a browser. Choose **Strict Honda** to see Type110 active with no secondary frame, or **Hypothetical Type111** to see a schematic synthetic cluster pattern, replay status, and event timeline. Press Control-C in the terminal to stop the local server.

The data file is generated from `synthetic_type111_cluster_replay()` in both modes. It summarizes the existing replay events and state; it does not include media bytes, key/IV material, or captured protocol payloads. The map-like pattern is an inline SVG illustration shown only when the replay records a mock renderer submission. It is not an H.264 decode or Honda image.

Evidence labels mean:

- `HONDA_CONFIRMED`: recovered stock Type110 behavior and Honda's unsupported Type111 branch.
- `MHI2_DERIVED_HYPOTHESIS`: prior-art candidate response profile, not a Honda wire contract.
- `SYNTHETIC_TEST_VALUE`: generated ports, identifiers, state, timestamps, and illustration.
- `UNKNOWN`: Honda response/security/correlation details and live integration surfaces that remain unproven.

The page intentionally keeps unknowns visible. Live Type111, jmcs no-op loading, and real ExternalDisplay rendering remain not ready.
