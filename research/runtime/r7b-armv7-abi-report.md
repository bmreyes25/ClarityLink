# R7B ARMv7 ABI report

Artifact: `build/r7b/android-armv7-r7b/libclaritylink_receiver.so` (ignored
build output; source build is reproducible with
`tools/build_android_api17_armv7.sh`). Local artifact SHA-256:
`eb6e8354f871cb69207954b3bf61f839ddbbcea04ec5eb1515388e23baf982ad`.

Inspection used NDK r23c `llvm-readelf -h -A -d`, `llvm-nm -D`, and host
`file`:

| Property | Observed |
|---|---|
| ELF class | ELF32 |
| Endianness | little-endian |
| Machine | ARM |
| EABI | EABI5 |
| ARM attributes | ARMv7 application profile, Thumb-2, VFPv3-D16 |
| NEON / VFPv4 | no mandatory build flags; assembly optimizations disabled |
| ELF type | shared library (DYN) |
| SONAME | `libclaritylink_receiver.so` |
| Interpreter | none (shared library, not executable) |
| NEEDED | `libm.so`, `libdl.so`, `libc.so` |
| C++ shared runtime | none; libc++ statically linked |

The wrapper target is `armv7a-linux-androideabi17`; compiler flags set
`-march=armv7-a -mfloat-abi=softfp -mfpu=vfpv3-d16`, and FFmpeg assembly/VFP/
NEON optimizations are disabled. No ARMv8, NEON, or VFPv4 requirement is
introduced. This matches the NDK's `armeabi-v7a` ABI toolchain. The vehicle's
actual CPU/runtime support remains unverified.

Result: `ANDROID_ARMV7_BUILD_CONFIRMED`. This label is not Honda execution or
compatibility evidence.
