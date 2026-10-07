# Step 43T1-R7B — Android API17 / ARMv7 native receiver build

Date: 2026-10-06. Starting point: R7A merge commit
`f0d800678684979277f9ad0b8f43c30153960eda` (PR #15 was verified OPEN,
mergeable, exact requested head `b125e894d3cf2e12c2c18d973fb9421cd05078ed`,
with Offline CI and CodeQL passing before a normal merge). R7B worktree began
clean at that exact merge SHA.

## Implementation

Added a C++17 generation-scoped receiver core, bounded per-stream transport
and media framing, independently owned test security/decoder/output resources,
FFmpeg H.264 decode, RGBA frame sinks, platform adapter interfaces, and a
synthetic native harness. Production authentication and both production media
security providers fail closed. The C++ `/info` transition and typed SETUP
model are not wire-compatible plist parsers; Python R7A remains the wire-flow
behavioral reference. The Android Surface class is a no-op fail-closed boundary.

Pinned Android NDK r23c 23.2.8568313 and FFmpeg 6.1.6. The FFmpeg release
signature verified using the upstream FFmpeg release signing key; its SHA-256
is also enforced by the target build script. The target build uses API17,
`armv7a-linux-androideabi17`, `armeabi-v7a`, C++17 and static libc++. Enabled
decoder is H.264 only; network, programs, encoders, GPL/nonfree features and
assembly optimizations are disabled.

## Test evidence

The native harness decodes two different H.264 assets, tests both stream
orderings, both single-stream configurations, secondary setup/display failure
isolation, malformed/truncated/oversized and unknown-type packets, stale
generation, duplicate IDs, decoder failure, disconnect, close idempotence,
concurrent receive/close, fail-closed production security, and 100 complete
dual-stream lifecycle cycles with per-cycle zero-resource assertions. Each
ordering/cycle delivered one 32x24 frame to each independent sink with correct
stream/generation association and differing content. See
`r7b-host-native-conformance.md`.

The ARM artifact was inspected as ELF32 little-endian ARM EABI5 with
`libclaritylink_receiver.so` SONAME. NEEDED dependencies are `libc.so`,
`libm.so`, `libdl.so`; no dynamic libc++ dependency is present. All 114 dynamic
imports match API17 NDK ARM stubs. No emulator/ARM runtime execution occurred.
Latest artifact SHA-256:
`eb6e8354f871cb69207954b3bf61f839ddbbcea04ec5eb1515388e23baf982ad`.
The target FFmpeg configuration enables H.264 decode only; parser, demuxer,
protocols, filters, encoders, network and assembly paths are disabled. The
complete API17 import list is in `research/runtime/r7b-api17-symbol-audit.json`.

ECC review found and fixed raw FFmpeg resource leaks on partial decoder
construction by replacing raw owning pointers with RAII deleters. Length,
allocation, pixel/dimension, stale-generation, duplicate-ID, and fail-closed
security checks were reviewed. Frame sinks are synchronous under the receiver
mutex and have an explicit non-reentrancy/no-throw contract. H.264 decoder
attack surface remains nontrivial despite bounded input/frame sizes.

ASan+UBSan and TSan host builds each passed the native lifecycle harness.
`clang-tidy` (clang-analyzer, bugprone and performance checks) found an
unnecessary shared-pointer-by-value parameter; it was changed to a const
reference. Its branch-clone diagnostic was excluded because each branch
constructs a distinct concrete primary/secondary provider. System-header
warnings were suppressed. `cppcheck` was unavailable. Full suite: 902 passed,
14 skipped; repository health and `git diff --check` passed. No target
sanitizer run is claimed.

## Evidence and gates

R7B host receiver behavior and fixture decoding are `HOST_NATIVE_CONFIRMED`.
API17/ARMv7 compilation and static ABI/import checks are
`ANDROID_ARMV7_BUILD_CONFIRMED`. These do not establish target runtime or Honda
compatibility. Genuine MFi/iPhone authentication, real SETUP, both real media
security paths, Type111 framing, Honda USB/iAP2 ownership, Display0/Display1,
cluster safety layout, audio/controls, Honda process lifecycle, and stock
restoration remain `EVIDENCE_REQUIRED`.

No Honda/vehicle/ADB action, APK installation, vehicle binary modification,
CAN/framebuffer operation, live Type111 negotiation, or CPC200 use occurred.

## Verification outcome

Exact implementation/final verification SHAs, hosted PR checks, final
decision, and recommended next milestone will be added after the checks run on
the final pushed HEAD. Older checks do not count.
