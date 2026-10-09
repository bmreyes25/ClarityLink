# R7E1 ELF, linkage, and static security audit

**Artifact:** `claritylink-target-diag`, SHA-256 `f2e12aafe221ff51e153ccc7c1b71402cf3cf0c3a4f1648fb5963e2e66cffca0`.

- `file` and `llvm-readelf`: ELF32, little-endian, ARM, EABI5 (`e_flags=0x5000200`), PIE, Android `/system/bin/linker` interpreter; ARMv7 attributes.
- NEEDED set: `libdl.so`, `libc.so`; both API17 standard platform libraries. No bundled/Honda dependency; mandatory unknown dependencies: zero.
- 10 unique imported symbols checked against NDK r23c API17 `libc.so`, `libm.so`, `libdl.so` stubs; zero unknown/post-API17 imports: `__cxa_atexit`, `__libc_init`, `__sF`, `clock_gettime`, `fputs`, `free`, `malloc`, `printf`, `puts`, `strcmp`.
- String scan found no CarPlay, MFi, iAP2, USB, `/dev/i2c-2`, Surface, Presentation, listener/server, HondaHack, jmcs, socket, or `/dev/` capability strings.
- Link is only the diagnostic C translation unit; no receiver, authentication, display, test bridge, or Honda code is linked. RELRO and immediate binding are enabled; binary is stripped.
- Argument parser accepts exactly zero or one supported switch. Extra/malformed/unknown options fail closed with status 2. Self-test allocation is fixed at 64 bytes, process-local, freed on every path; no file/network/device operations or daemonization exist.

The separate APK is framework-dependent and is not part of the Test A ELF audit. APK package metadata reports min SDK 17/target SDK 17 and no permissions. Its display-related code is separate and the Presentation/single-frame modes are emulator-gated with explicit acknowledgement.
