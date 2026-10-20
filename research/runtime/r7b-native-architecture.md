# R7B native architecture

The R7A Python receiver remains the host behavioral reference. R7B adds a
generation-scoped C++17 receiver under `native/`, rather than translating the
Python framework line by line. One `ReceiverGeneration` owns two optional
streams. Each stream owns its connection ID, fail-closed or synthetic test
security provider, H.264 decoder context, and one output sink. The parent
generation serializes setup, receive, close, and teardown with one mutex.
Authentication enters through `AuthenticationAuthority`: only the explicit
`SyntheticTestAuthenticationAuthority` activates the offline harness;
`UnavailableAuthenticationAuthority` leaves the receiver idle. No production
credential, MFi mechanism, or real-iPhone authentication is supplied.

Setup validates all requested stream enums and IDs before allocation, then
commits each stream independently. A secondary setup failure after a valid
primary setup leaves Type110 usable. Duplicate IDs, duplicate active stream
types, stale generations, malformed wire lengths, unknown stream types, and
post-close media are rejected. Close is idempotent, clears both outputs, and
destroys child decoder/security/transport ownership. A stream close only clears
its own logical output.

The native bounded media envelope is a 15-byte header: big-endian generation
(8), stream type (1), connection ID (2), payload length (4), followed by a
single H.264 access unit. The fixed maximum access unit is 2 MiB. Each stream
owns a separate `MediaTransport`; the current host implementation is a bounded
vector-backed test transport, not an OS socket listener. Honda TCP/USB
transport parsing and endpoint allocation are deliberately not implemented.
`/info` is modeled as a generation-bound state transition, while the existing
Python implementation remains the actual plist `/info` and SETUP reference;
C++ does not claim wire-compatible plist parsing.

The host path uses native libavcodec calls and libswscale to produce owned RGBA
frames. Output frames carry stream, generation, timestamp, dimensions, stride,
and pixels. Memory sinks are independent. `AndroidSurfaceBoundary` is a
compile-valid fail-closed API seam only; it has no JNI Surface bridge. Platform
ports for clock, thread, socket, display, audio, input, USB, authentication,
and process lifecycle are interface-only.

ECC review findings and fixes: (1) initial decoder objects used raw FFmpeg
pointers and could leak if construction failed midway; all codec/frame/packet/
scale contexts now use RAII deleters. (2) peer-controlled lengths are bounded
before allocation and exact packet length is checked before payload copying.
(3) decoded dimensions/pixel count and RGBA byte count are capped. (4) display
callbacks are synchronous under the generation mutex, so the FrameSink contract
explicitly prohibits re-entry into the owner; test sinks follow that contract.
(5) production security providers return failure and do not pass bytes through.
No speculative cryptography was added.

Limitations: host logical sinks only; no target runtime/emulator was available.
OS listeners and native plist parsing are not implemented.
The frame sink must obey its documented non-reentrant contract. Native Android
audio, input, USB/iAP2, authentication, and process integrations remain future
boundaries, not implemented adapters.

## Adapter boundary inventory

| Boundary | R7B state | Honda status |
|---|---|---|
| Authentication authority | `AuthenticationAuthority` interface; synthetic and unavailable implementations | Genuine authority `EVIDENCE_REQUIRED` |
| USB/iAP2 transport | `PlatformUsb` interface | `EVIDENCE_REQUIRED` |
| Control-session transport | `PlatformSocket` contract; no Honda control adapter | `EVIDENCE_REQUIRED` |
| Media transport | `MediaTransport`; vector-backed host test transport | Honda socket/USB ownership `EVIDENCE_REQUIRED` |
| Audio output | `PlatformAudio` interface | `EVIDENCE_REQUIRED` |
| Input/steering controls | `PlatformInput` interface | `EVIDENCE_REQUIRED` |
| Primary display | host `FrameSink` tested; generic `PlatformDisplay` boundary | Honda Display0 admission `EVIDENCE_REQUIRED` |
| Secondary display | separate host `FrameSink` tested; fail-closed `AndroidSurfaceBoundary` | Honda Display1 admission/safe area `EVIDENCE_REQUIRED` |
| Process lifecycle | `PlatformProcessLifecycle` interface | Honda lifecycle/stock restoration `EVIDENCE_REQUIRED` |

The API-level platform interfaces are `INTERFACE_COMPLETE` only. They do not
claim `ANDROID_API_DOCUMENTED` behavior for Honda, Android Surface admission,
audio routing, USB ownership, or process policy.
