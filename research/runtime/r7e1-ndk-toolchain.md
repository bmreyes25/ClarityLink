# R7E1 NDK toolchain and provenance

**Result:** pinned Android NDK r23c was already present and reused; no SDK/NDK installation or download occurred.

| Field | Value |
|---|---|
| NDK revision | `23.2.8568313` (r23c) |
| Path | `$HOME/Android/r7c2-sdk/ndk/23.2.8568313` |
| Host toolchain | `toolchains/llvm/prebuilt/darwin-x86_64` |
| Clang | 12.0.9 (NDK build) |
| Target wrapper | `armv7a-linux-androideabi17-clang` |
| API | 17 |
| Source revision embedded in ARM binary | `5b1d490d79f2e4ffa9c11be8aff0a9142b5dc2d6` |

The toolchain path and revision match earlier R7C provenance in `research/runtime/r7c2-ndk-recovery.md`, `r7b-toolchain-selection.md`, and `r7c-build-provenance.md`. The build script checks `source.properties` before invoking the compiler. No global shell configuration was changed.

Reproduce with `ANDROID_NDK_HOME="$HOME/Android/r7c2-sdk/ndk/23.2.8568313" ./tools/build_r7e1_target_diag.sh`. Build outputs and audit files are ignored under `build/r7e1/`.
