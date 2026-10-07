# 43T1-R7C — Honda-target adapter implementation (offline)

**R7B merge / R7C starting HEAD:** `087f17fb9268f623eabd520c3542b00db0d512b9` (PR #16 merged to `main`).
**Branch/worktree:** `architecture/r7c-honda-target-adapters` / `clarity-r7c-honda-adapters`.
**Scope:** generic Android API17 adapters and offline host checks only. No Honda, ADB, APK install, `/dev/i2c-2`, live negotiation, CAN, or framebuffer execution.

## Implementation

- Added API17 Java display discovery, Activity-owned Display0 Surface host, fail-closed Presentation candidate, USB host API boundary, AudioTrack PCM output, input allowlist, unavailable iAP2/auth providers, capability evidence model, process lifecycle, diagnostics, bounded metrics, and test mock host.
- Added opaque JNI registry handles, generation/stream-bound surfaces, start/setup/disconnect/release, and an explicit lab-only synthetic packet entry point. Production construction defaults to unavailable authentication; synthetic framing is never used as CarPlay wire framing.
- Added generic `ANativeWindow_fromSurface` backed RGBA sink with dimension/stride/byte bounds, per-generation/stream checks, clear, invalidation, and RAII reference ownership; added numeric IPv4 POSIX socket adapter with explicit local bind and bounded operations.
- Added 12 architecture/readiness/evidence notes and build/audit scripts. Build products and downloaded SDK platform archive are ignored under `build/`.

## ECC review findings and fixes

1. **ANativeWindow/JNI lifetime:** conversion returns a native reference; sink takes its own ref and releases the temporary. Surface release invalidates the sink before releasing its owned ref. Opaque registry IDs reject invalid/double release. Receiver retains `shared_ptr` safely after Java handle loss.
2. **Buffer arithmetic/pixel stride:** RGBA format is explicit. Width/height, source stride, exact vector length, destination stride, and max frame bytes are checked before row copies; no unbounded frame copy.
3. **Generation/stream ownership:** sink and receiver must agree on generation and Type110/Type111. Connection IDs are explicit setup inputs, range-checked, and duplicate-checked rather than guessed. Stale frames are rejected. Separate outputs remain independent; there is no Type111-to-Display0 fallback.
4. **Lock ordering/reentrancy:** registry lock is released before receiver and surface operations; native sink does not invoke Java; receiver-to-sink locking follows the synchronous FrameSink contract. Java Presentation operations are application/UI-owned.
5. **JNI exceptions:** validation failures become Java `IllegalStateException`; native allocation/setup/packet exceptions are contained at JNI and translated to sanitized Java errors.
6. **Socket/parser boundary:** socket remote and local bind are numeric non-wildcard IPv4; connect/read/write are bounded and generation checked. Writes suppress SIGPIPE. Synthetic packet framing is exposed only on explicit lab-mode receiver handles, capped at R7B maximum, and is not a CarPlay parser.
7. **USB/auth/input:** USB requires Android permission and checks generation/transfer bounds; no Honda descriptor selection or iAP2 packets are added. Default auth is unavailable. Input requires an explicit source/type/code allowlist; empty Honda default rejects all events.
8. **Warning/safe-area policy:** UNKNOWN fails closed; Presentation refuses test-only layout and missing approved warning policy. Static display existence is not promoted to admission or warning safety.
9. **Dependencies/API:** API17 Java source compilation uses the official Android 4.2.2 platform `android.jar`; Android NDK r23c targets API17/armeabi-v7a. FFmpeg 6.1.6 archive is SHA-256 checked by the R7B build script. Dynamic imports were checked against API17 libc/libm/libdl/libandroid stubs.
10. **Remaining ECC validation gap:** JNI invalid-handle/double-release, Java/native callback races, ANativeWindow destruction races, JNI-path TSan, and integrated Android adapter resource-cycle tests were not available on this host. Socket TSan and R7B receiver TSan did run and passed. These gaps prevent a full R7C pass.

## Verification

- Android Java compilation against API17: **PASS** (`tools/test_r7c_java_api17.sh`); Java 7 source/target warnings from JDK 17 only.
- Java fail-closed warning/layout and process lifecycle harness: **PASS**, 100 process-resource cycles. This does not exercise JNI, Android framework, decoders, or displays.
- API17 ARMv7 native adapter shared library: **PASS**, NDK r23c/API17; ELF32 ARM EABI5, `libandroid.so` + libc/libm/libdl only; API17 stub audit has zero unknown imports. Artifact: `build/r7c/android-armv7/libclaritylink_android.so` (ignored, not committed).
- Host POSIX socket tests: **PASS** for loopback, wildcard rejection, port conflict, generation mismatch, transfer bound, peer close; ASan/UBSan run passed.
- R7A Python regressions: **PASS** as part of repository suite; R7B native decoder regressions: **PASS**, 100 native cycles, dual streams, Type111 isolation; ASan/UBSan R7B host build passed.
- Full repository suite: **902 passed, 14 skipped**. Repository health and whitespace validation are recorded at final revision.
- Missing: R7C JNI automated tests; Android Surface runtime/instrumentation; full 100-cycle receiver+all-adapter integration; Android emulator target simulation; TSan; complete audio/input/USB/iAP2 failure matrix.

## Evidence state and decision

`ANDROID_API_DOCUMENTED` and `ANDROID_ARMV7_BUILD_CONFIRMED` apply to API availability/build artifact only. Display1 admission, warning coexistence, safe area, Honda audio/controls, USB ownership, genuine MFi, actual iPhone metadata/setup, real Type110/Type111 security/framing, executable acceptance, and stock restoration remain `EVIDENCE_REQUIRED`. R6C/R6D classifications are preserved: Honda auth is internal to jmcs and no supported external authenticated-session handoff was found.

Explicit unresolved gates: `REAL_MFI_AUTH = EVIDENCE_REQUIRED`; `REAL_IPHONE_INFO = EVIDENCE_REQUIRED`; `REAL_IPHONE_SETUP = EVIDENCE_REQUIRED`; `REAL_TYPE110_SECURITY = EVIDENCE_REQUIRED`; `REAL_TYPE111_SECURITY = EVIDENCE_REQUIRED`; `REAL_TYPE111_FRAMING = EVIDENCE_REQUIRED`; `HONDA_EXECUTABLE = EVIDENCE_REQUIRED`; `HONDA_DISPLAY0 = EVIDENCE_REQUIRED`; `HONDA_DISPLAY1 = EVIDENCE_REQUIRED`; `HONDA_WARNING_SAFETY = EVIDENCE_REQUIRED`; `HONDA_AUDIO = EVIDENCE_REQUIRED`; `HONDA_CONTROLS = EVIDENCE_REQUIRED`; `HONDA_USB_OWNERSHIP = EVIDENCE_REQUIRED`; `HONDA_STOCK_RESTORATION = EVIDENCE_REQUIRED`.

**Decision: `R7C_INTEGRATION_PARTIAL`**. The native and Java pieces compile, but the JNI/display/audio/USB/input stack is not yet covered by the full integration and lifecycle test matrix. Next: close the R7C integration test gaps in a separate offline iteration before R7D. No Honda/vehicle execution occurred.
