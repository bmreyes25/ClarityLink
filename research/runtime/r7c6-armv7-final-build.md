# R7C6 ARMv7 final build

Fresh build used Android NDK r23c (23.2.8568313) and target
`armv7a-linux-androideabi17`, ABI `armeabi-v7a`.

- Artifact: `build/r7c/android-armv7/libclaritylink_android.so`
- SHA256: `a53b18813024a44150e7eba1cfaba106f7d7a7e911602392ee63ff869fffd51d`
- ELF: ELF32, little-endian, ARM, EABI5, ARMv7, VFPv3-D16
- SONAME: `libclaritylink_android.so`
- NEEDED: `libandroid.so`, `libm.so`, `libdl.so`, `libc.so`
- API17 stub audit: zero unknown imports
- JNI and ANativeWindow symbols: linked in the production target
- POSIX socket imports: resolved against API17 Bionic

The diagnostic race-controller translation unit is excluded from this ARM
production build. Build outputs remain ignored and are not committed.
