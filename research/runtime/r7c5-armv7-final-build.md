# R7C5 ARMv7 final build

**Result: PASS for the current local source tree; this artifact is not a pushed PR artifact.**

- NDK: r23c, `23.2.8568313`.
- Target: `armv7a-linux-androideabi17`, ABI `armeabi-v7a`.
- ELF: ELF32, little-endian, ARM, EABI5, ARMv7 application profile.
- SONAME: `libclaritylink_android.so`.
- NEEDED: `libandroid.so`, `libm.so`, `libdl.so`, `libc.so`.
- Import audit: checked API17 `libc`, `libm`, `libdl`, and `libandroid` stubs; **zero unknown imports**. ANativeWindow and POSIX socket symbols resolved.
- Artifact SHA-256: `00ebf5a3385817949e2d7cfac7eef89e9759a40ee9f0310dbaeb06fa4764fa89`.

The build script links the production receiver, Surface sink, socket adapter, JNI bridge, and FFmpeg 6.1.6 static libraries. Build output is ignored and was not added to Git. This build does not close framework race, Dalvik fault-matrix, hosted-check, or merge gates.
