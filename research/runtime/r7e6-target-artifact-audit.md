# R7E6 target diagnostic artifact audit

The ARMv7 diagnostic was rebuilt from the process-supervisor source with pinned NDK r23c for `armv7a-linux-androideabi17` / API17.

- Size: 7,904 bytes
- SHA-256: `3eecced4b46585b79566d7a17ebd5c692883c83e88db92447128a1e215ade42a`
- MD5: `b6d64f70999739bc0f180c6cda923342`
- ELF: ELF32, little-endian, ARM, EABI5, PIE
- `DT_NEEDED`: `libdl.so`, `libc.so`
- Imports: `__cxa_atexit`, `__libc_init`, `__errno`, `__sF`, `_exit`, `alarm`, `clock_gettime`, `fflush`, `fork`, `fputs`, `free`, `getpid`, `kill`, `malloc`, `memset`, `nanosleep`, `pause`, `printf`, `puts`, `sigaction`, `sigpending`, `sigprocmask`, `sigwait`, `strcmp`, `waitpid`
- API17 pinned-stub and artifact checker: passed.
- Ignored staging copy: mode `0555`, byte-identical; same SHA-256 and MD5.

Source and import inspection found only the bounded diagnostic modes and their process/signal support. A raw capability-string scan found the benign self-test status token `LISTENERS=0`; there are no socket/listener imports or calls. The executable includes no display, framebuffer, SurfaceFlinger, USB/iAP2, MFi, CarPlay, vehicle device path, CAN, HondaHack, or jmcs functionality. Test-only fault modes are compiled separately and are not present in this production artifact.

The earlier R7E5F digest is historical and superseded. This audit does not establish target dynamic loading or runtime operation; the API17 emulator gate is blocked by ADB isolation on this host.
