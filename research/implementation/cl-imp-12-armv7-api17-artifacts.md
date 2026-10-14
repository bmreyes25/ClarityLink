# CL-IMP-12 ARMv7/API17 artifact preparation — 2026-10-13

## Result

A repeatable packaging workflow now builds a 32-bit ARMv7/API17 JNI/native library, compiles the API17 Java adapter JAR, builds the API17 emulator-only test APK and separately disabled candidate APK, audits API17 native symbol availability, and emits build/dependency/permission/compatibility manifests plus SHA-256 sums. Outputs are local ignored artifacts under `build/cl-imp-12/artifacts/`; no binary artifacts are committed.

The native `.so` is an independently packaged library and is not currently loaded by the Java lab APK. The disabled candidate remains disabled in its manifest and is not installed. This milestone does not establish Honda permission, display, authenticated-session, or deployment compatibility.

## Validation

- ARMv7 API17 shared JNI/native library build: passed with pinned NDK r23c `23.2.8568313` and FFmpeg 6.1.6 static H.264 decoder build.
- Native symbol audit against API17 Bionic and `libandroid` stubs: passed with zero unknown imports.
- API17 Java compile: passed targeting Java 7 APIs. The JDK emitted the expected obsolete source/target warnings.
- Lab APK and disabled candidate APK build: passed; each declares zero Android permissions. The candidate application and activity remain disabled.
- API17 x86 emulator decoder test: passed for two streams and the 32×32→64×64 reset; reports Surface submission only.
- API17 x86 emulator Presentation/content test: passed for install/admission/Canvas drawing/private frame IPC/lifecycle cleanup/uninstall. This is emulator-only evidence and does not prove physical scanout.
- Packaging rerun: all five packaged artifact hashes matched across two consecutive complete builds.
- Focused packaging contract tests: 4 passed. Configured offline regression: 1,425 passed, 14 skipped; self-locator smoke and simulator JavaScript checks passed. Repository health and `git diff --check` pass.
- ECC packaging/security checklist review: no blockers identified. It covered pinned source/toolchain inputs, zero unknown dynamic imports, deterministic outputs, no APK permissions, disabled candidate state, ignored signing-key handling, and build-only output paths. This was an in-session checklist review, not an independent reviewer attestation.

## Package inventory

`build/cl-imp-12/artifacts/` contains the ARMv7 shared library, API17 Java JAR, emulator-only test APK, disabled candidate APK, API17 symbol audit, JSON build manifest, dependency inventory, permission inventory, compatibility report, and `SHA256SUMS`. Current SHA-256 values:

- `api17-symbol-audit.json` (5095 bytes): `9ac23d691c35c5074a875a04bd00b9ef4bb93bcd49c71e14cdadbd1106a6cf94`
- `claritylink-android-api17.jar` (70239 bytes): `d4fe4d5840ad9dd5d14670a17337425b71ebf5e92f1a329a95d5885c28def677`
- `claritylink-disabled-candidate.apk` (37488 bytes): `3b702a19adf6f58a3818813fcaa7e4f445dafbcf7b9f6ed6cae8d45c8f4d4599`
- `claritylink-display-lab.apk` (44134 bytes): `b8cbe434c053529f475f9a7be2a3122d1a8dc6bbd7a3a0c9b3c4d96704282e63`
- `libclaritylink_android.armv7.so` (2250996 bytes): `ebba888796584d583493194155a0f997e6ac279f5da89e1271ac4030509d19c9`

Permission inventory reports no Android permissions for either APK. Dependency inventory pins the SDK platform and build tools, NDK, FFmpeg archive hash, Java source target, native shared-library dependencies, and the local debug signing-key assumption. APK repeat hashes are stable when the same ignored local keystore is retained; creating a new signing key changes APK hashes. See the generated JSON reports for machine-readable details.

## Remaining limits

The native library and Java/API17 components are not yet an end-to-end packaged Android receiver. The lab APK is a test adapter, and the candidate APK is disabled. No authentic Type111 security/session, real iPhone media, Honda Display 1 admission, physical cluster geometry or scanout, vehicle operation, or Honda installation was performed. Production Honda integration remains disabled.
