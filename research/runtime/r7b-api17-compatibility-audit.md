# R7B Android API17 compatibility audit

## Result

The target was compiled with NDK r23c's API17 compiler wrapper and sysroot.
The post-link checker `tools/audit_android_api17_symbols.py` compares every
undefined dynamic symbol with the NDK's API17 ARM `libc.so`, `libm.so`, and
`libdl.so` stubs. It found 114 distinct imports, all present in those API17
stubs; no mandatory `UNKNOWN` import was found. Linking against the API17
sysroot also makes newer system symbols fail at link time.

Observed NEEDED libraries: `libc.so`, `libm.so`, `libdl.so`. No Java/JNI
framework methods are called by the native artifact. `AndroidSurfaceBoundary`
is a C++ fail-closed placeholder only. Platform interfaces for audio, input,
USB, authentication, and lifecycle are not implementations.

The complete per-symbol classification tied to the artifact SHA-256 is in
[`r7b-api17-symbol-audit.json`](r7b-api17-symbol-audit.json). API17 imports
include `clock_gettime`, `gettimeofday`, `nanosleep`, basic
pthread mutex/condition/thread/key functions, `sched_getaffinity`, ordinary
POSIX socket-independent libc calls, math functions, allocation, and unwind
entrypoints. The NDK API17 stubs provide each imported symbol. No
`std::filesystem`, modern dynamic loader calls, newer property API, or JNI API
is used. C++ runtime code is statically linked; `libc++_shared.so` is not
required on the target.

The symbol check is a static API-surface audit, not proof that the Honda's
particular Bionic build, linker, process policy, or runtime environment can load
and execute the artifact. Old-Bionic runtime behavior remains
`EVIDENCE_REQUIRED`.

## Classification

| Area | Classification | Evidence |
|---|---|---|
| libc/Bionic external symbols | API17_AVAILABLE | API17 NDK stubs + successful API17 link |
| libm/libdl | API17_AVAILABLE | API17 NDK stubs + NEEDED list |
| C++ runtime | BUNDLED_RUNTIME | static NDK libc++ link; no shared libc++ NEEDED |
| project decoder/core | PROJECT_OWNED | linked receiver library + static FFmpeg archives |
| Android Surface/JNI | LATER_ANDROID | boundary only, no JNI/framework method |
| Honda runtime symbols | UNKNOWN | no Honda execution and no target binary analysis |
