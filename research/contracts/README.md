# Independent CarPlay display boundary contract

`cluster-stream-v1.schema.json` is the authoritative **offline bench** event contract between a proposed receiver adapter (provider) and a display-1 cluster renderer (consumer). The research owner approves contract changes. It is not an Apple protocol definition and is not an ABI to patch directly into the car.

The consumer's job is narrow: display decoded cluster navigation frames inside a measured navigation-only area, preserve the existing CarPlay audio path, and clear the surface at route end, error, or disconnect. It cannot request or carry vehicle-bus data. The provider owns CarPlay capability advertisement, setup, decoding, and lifecycle; it exposes opaque `bench://` frame references rather than raw pixels in JSON.

Version `1.0.0` defines session, display, stream, frame, stop, and error events. Unknown fields are rejected. Safe areas must be contained within view areas, which must be contained within the display. A trace cannot activate an unconfigured stream, skip frame sequence values, leave a stream active at session stop, or emit events after the session ends. Breaking changes require a new major version; compatible optional behavior requires a new schema version and fixtures before implementations change.

Run from the analysis root:

```sh
node research/contracts/validate-cluster-stream.js
node research/contracts/test-cluster-stream.js
```

The valid fixture models an 800×480 center display at 30 FPS and a hypothetical 800×480 cluster map at 15 FPS. Those values are an offline test profile. Only the center dimensions/rate are confirmed in Honda's copied configuration; the cluster safe area and decoder capacity remain unverified.
