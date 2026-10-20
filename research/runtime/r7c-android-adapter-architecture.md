# R7C Android adapter architecture

**Base:** R7B merge `087f17fb9268f623eabd520c3542b00db0d512b9`. Offline generic API17 / ARMv7 code only; no Honda execution.

## Ownership

`ReceiverGeneration` remains the single session owner. Java owns Android objects and UI callbacks. JNI maps positive opaque IDs to shared native owners; raw pointers never cross into Java. `AndroidSurfaceSink` acquires one `ANativeWindow` and owns a generation, stream, and surface token. Surface destruction invalidates the sink before handle removal. Receiver close is idempotent and clears outputs; Type111 output failure does not reroute to Display0.

The native wrapper exposes start/setup/disconnect/release and an explicit `labMode` switch. Lab mode creates synthetic authentication and must only be selected by an offline test harness. Default mode uses `UnavailableAuthenticationAuthority`. JNI does not parse CarPlay control or real media framing. R7B's 15-byte test packet is not CarPlay framing.

## Platform boundaries

- Display0: Java-hosted Surface supplied by an application Activity; no Honda window policy.
- Display1: `DisplayManager` inventory and API17 `Presentation` candidate; admission is tracked as separate states, and Honda warning/safe-area evidence is mandatory before candidate use.
- Transport: IPv4 numeric-address socket with bounded poll/read/write; no wildcard or guessed endpoint. Synthetic test framing is distinct from disabled `CarPlayMediaTransport`.
- USB: API12+ public host plumbing only. USB permission does not establish factory-accessory ownership or CarPlay authority. iAP2 is a separate unavailable contract.
- Authentication: unavailable by default. No `jmcs` handoff or `/dev/i2c-2` path.
- Audio/input: generic Android output and allowlisted event contract. Routing/key maps are not Honda facts.
- Lifecycle/restoration: closes only ClarityLink-owned resources. It does not assert factory Honda restoration.

## ECC review

Frame-copy arithmetic and dimensions are bounded; generation/stream mismatch rejects frames; handles are registry IDs with explicit release errors; native callbacks do not call Java. JNI registry locks are released before receiver close or sink invalidation. Type111 never falls back to primary. Warning evidence defaults UNKNOWN. API17 Java source compiled and the API17 ARMv7 native library passed its stub audit. Automated JNI/thread/lifecycle integration tests remain incomplete.

Android API evidence: [DisplayManager API17](https://developer.android.com/reference/android/hardware/display/DisplayManager), [Presentation API17](https://developer.android.com/reference/android/app/Presentation), [USB host API12](https://developer.android.com/reference/android/hardware/usb/UsbManager), and [NDK ANativeWindow Surface conversion](https://developer.android.com/ndk/reference/group/native-activity#ANativeWindow_fromSurface).
