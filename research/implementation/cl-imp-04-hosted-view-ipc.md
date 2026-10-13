# CL-IMP-04 — Hosted-view IPC and simulated compositor

**Status:** implemented and validated on the isolated Android 4.2.2/API 17 x86 emulator. All exchanged pixels are synthetic lab data. Honda production integration remains disabled.

## Process and transport boundary

- The API17 lab APK binds a non-exported `CompositorService` in its own `:compositor` process. The disabled candidate APK declares the service disabled too. Neither manifest requests permissions.
- The protocol is versioned and private to the package. The service rejects callers outside the app UID and rejects unknown protocol versions.
- Binder transactions carry bounded frame metadata and a `ParcelFileDescriptor` pipe. Pixel bytes are streamed in 8 KiB chunks rather than placed in Binder's transaction buffer. The receiver accepts at most 4 MiB, validates dimensions/stride/exact byte count and EOF, and keeps no frame-sized copy.
- `FrameBackpressureGate` permits one in-flight frame. The simulated compositor rejects stale generations, non-increasing timestamps and malformed/oversized frames. A generation-scoped Binder warning transaction signals warning visibility; the model clears its current-frame accounting and blocks frames until warning clear. No Honda warning source or actual surface blanking is integrated or proven. Matching session end clears the generation and retained metadata; binding/process teardown destroys the service. Each pipe endpoint has one stream owner, and the stream auto-closes its `ParcelFileDescriptor`.

## Demonstration and evidence

- The emulator runner observed distinct Activity and compositor PIDs, a synthetic frame drawn by the Presentation-hosted View's Canvas, the same generation/timestamp/16-byte payload accepted by the compositor process, then an explicit session end and service-process teardown on display removal.
- The crash-recovery scenario also relayed the synthetic frame before the injected Activity crash. After the runner dismissed Android 4.2.2's crash dialog with `force-stop`, both the app-owned window and the recorded compositor PID were absent; relaunch remained status-only. The candidate APK was never installed.
- Focused CL-IMP-03/04 contract tests: 10 passed. API17 Java policy/lifecycle/frame/compositor tests passed. Full offline regression: 1,377 passed, 14 skipped; 3 self-locator checks and simulator checks passed. Repository health and whitespace checks passed.
- API17 lab APK SHA-256: `1f08435c2a58a6ea5cbde7c78b132cef7cd06816067634608daa5444501feb4b`. Disabled candidate APK SHA-256: `35bf02bb4d5cd217326de4700bc9d2da3718731e3ba538e5c36437ce1cdb6afa`.

## Limits

The second process is a ClarityLink-owned compositor **model**. It validates and records metadata for the accepted frame but does not acquire an ExternalDisplay or Honda surface, draw pixels into another process's View, or prove physical scanout. The warning transaction validates only the lab protocol/model path and does not blank a rendered or physical display. This milestone uses bounded pipe IPC, not shared memory. No Honda process, vehicle, stock process, or live iPhone was accessed. Honda IPC/display APIs, Type111 negotiation/security, authenticated iPhone navigation content, production permission/warning behavior and measured cluster safe area remain unproven.
