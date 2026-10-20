# 43T1-R7C1 — Honda adapter integration closure (offline)

**R7C1 starting HEAD:** `25bf1436f71587e9984940b88d7766a9fa2f44fb` on `architecture/r7c-honda-target-adapters` (PR #17). The R7C report's `fc9a70d…` hosted-check SHA is a historical pre-R7C1 revision; R7C1 changes require new exact-head hosted checks.

**Scope:** close host-testable JNI handle, Surface lifecycle, receiver integration, and resource accounting gaps. No Honda, ADB, APK install, `/dev/i2c-2`, live CarPlay negotiation, CAN, framebuffer, startup modification, or vehicle execution occurred.

## Changes and ECC findings

1. **Stale-generation clear (risk: retained secondary output):** the native Stream destructor passed generation `0` to `FrameSink::clear`. Added an owner generation to each Stream and clear with the actual generation. The integrated run verifies all-zero surface buffers after shutdown.
2. **Surface test boundary (risk: untested lock/copy/release behavior):** extracted `SurfaceSinkCore` and the narrow `SurfaceWindow` interface. `AndroidSurfaceSink` continues to use real API17 ANativeWindow acquire, geometry, lock, post, release calls. The host fake exercises the same core without claiming Android runtime behavior.
3. **Surface copy/race (risk: overrun or backend release during frame copy):** generation/stream, dimensions, exact source length, row stride, destination dimensions and destination byte limits are checked. A core mutex serializes present/clear/invalidate; test synchronization uses a condition variable, not sleeps.
4. **Stale JNI handle ABA (risk: old Java long resolving to another native owner):** added one process-lifetime monotonic ID allocator and synchronized opaque handle tables, shared by receiver and surface registries. IDs are not recycled, use-after-release is rejected, in-flight `shared_ptr` owners survive table erase, and allocator exhaustion fails closed.
5. **Primary versus secondary failure (risk: false “active” state after loss of center path):** Type111 media/sink failure drops only Type111 and preserves Type110. Type110 decode/output failure clears both streams and transitions the model session to `Closed`.
6. **JNI exception/thread boundary:** registry locks are released before owner operations. JNI exception and native exception translation remain as before. No native-created JNI worker thread or Java callback exists; ART exception/reference/attach semantics were not dynamically tested.

## Test results

| Category | Result | Environment and evidence |
|---|---|---|
| Handle table | PASS: 2,000 concurrent allocations, stale handle, retained in-flight owner, invalid release, overflow | Host C++17; exact shared allocator/table used by JNI. ASan/UBSan and TSan passed. |
| Surface lifecycle core | PASS: padded-stride RGBA copy, clear, mismatch/bounds rejection, geometry/lock/post errors, replacement, repeated invalidation, deterministic invalidate/frame race | Host fake backend (`HOST_SIMULATED_ANDROID_RUNTIME`). ASan/UBSan and TSan passed. |
| Integrated receiver/surface path | PASS: actual FFmpeg H.264 fixtures decode through `ReceiverGeneration` into Type110/Type111 `SurfaceSinkCore` buffers, distinct output bytes and dimensions | Host FFmpeg 9.0.2, not Android framework. |
| 100-cycle integrated model | PASS: 100/100 cycles checked individually; receiver, modeled owner counters, JNI table, decoders/streams, and surfaces return to zero/cleared per cycle | Host-simulated Android adapter ownership; actual receiver decoder and surface core. |
| Type111 isolation | PASS for unavailable surface, surface loss after a frame, and malformed secondary media; Type110 remains usable and Type111 resources are released | Host core/receiver integration. |
| Type110 failure policy | PASS: primary surface fault closes the model session and rejects later Type111 input | Host core/receiver integration. |
| Production auth/security | PASS fail-closed with unavailable authority/security provider | Receiver model only; no genuine authority. |
| R7A/R7B/repository | R7A suite and R7B native ASan/UBSan + TSan passed; repository suite `902 passed, 14 skipped`; health check passed | Host/local. |
| API17 Java and ARMv7 | Java API17 build/policy harness passed; JNI/native shared object rebuilt for API17/armeabi-v7a, ELF32 ARM EABI5; import audit: four expected stub libraries, zero unknown imports | Cross-compile only, no Android runtime execution. |

The initial R7B ASan/TSan invocations shared an ignored build output path, so they were repeated sequentially after the receiver changes; both sequential runs passed. R7C1 integrated ASan/UBSan and TSan runs also passed.

## R7C1 acceptance gaps that remain

This does **not** complete the all-adapter closure. The C++ harness tracks offline leases for audio, input, USB, iAP2, auth and socket; it does not call those Java adapter implementations end-to-end. Socket loopback/bounds tests are separate, not inside each integrated cycle. The actual JNI exported entrypoints were cross-compiled but not loaded in a JVM. ART exception propagation, Java callback during teardown, local/global reference lifecycle, attach/detach, Android Surface/ANativeWindow runtime, Presentation creation/admission, Java audio failure during video, USB permission/endpoint callbacks, and full process-stop race matrix are not dynamically covered. No Android emulator/JVM was available or run.

The focused fault set covers primary and secondary output/media failures, stale/wrong generations and stream, Surface backend operation failures, invalid/released handles, production auth/security refusal, and existing POSIX socket cases. It does not exhaust the user's full requested process/JNI/Java/USB/iAP2/audio/socket callback failure matrix. The complete 100-cycle integrated Android adapter test criterion therefore remains open even though 100 host receiver+surface-core cycles pass.

Exact current PR-head Offline CI and CodeQL must be verified after this R7C1 commit is pushed. The earlier R7C hosted pass on `fc9a70d…` does not certify R7C1 changes.

## Honda evidence gates preserved

`REAL_MFI_AUTH`, `REAL_IPHONE_INFO`, `REAL_IPHONE_SETUP`, `REAL_TYPE110_SECURITY`, `REAL_TYPE111_SECURITY`, `REAL_TYPE111_FRAMING`, `HONDA_EXECUTABLE`, `HONDA_DISPLAY0`, `HONDA_DISPLAY1`, `HONDA_WARNING_SAFETY`, `HONDA_SAFE_AREA`, `HONDA_USB_OWNERSHIP`, `HONDA_AUDIO`, `HONDA_CONTROLS`, and `HONDA_STOCK_RESTORATION` remain `EVIDENCE_REQUIRED`.

**R7C1 final decision: `R7C_INTEGRATION_PARTIAL`.** The production API17 adapter compiles and meaningful native receiver/surface-core integration now passes, but the full JNI/Android/Java all-adapter test matrix is incomplete. The R7D entry gate remains closed. Next action: `GO_FOR_R7C_INTEGRATION_CLOSURE`.
