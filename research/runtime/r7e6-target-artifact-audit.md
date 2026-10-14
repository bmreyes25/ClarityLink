# R7E6 target diagnostic artifact audit

The ARMv7 diagnostic was rebuilt from the process-supervisor source at commit `cd1d47b51f84e7f0c79a28f079f620fcd4ee0631`, using pinned NDK r23c for `armv7a-linux-androideabi17` / API17.

- Size: 7,904 bytes
- SHA-256: `9e20d1ad715be6c9974f9a89e1aa310283bc128f87350fb05cb224b8e247c063`
- MD5: `6137a693a77646aaf9a4cf0f351731d4`
- ELF: ELF32, little-endian, ARM, EABI5, PIE
- `DT_NEEDED`: `libdl.so`, `libc.so`
- Imports: `__cxa_atexit`, `__libc_init`, `__errno`, `__sF`, `_exit`, `alarm`, `clock_gettime`, `fflush`, `fork`, `fputs`, `free`, `getpid`, `kill`, `malloc`, `memset`, `nanosleep`, `pause`, `printf`, `puts`, `sigaction`, `sigpending`, `sigprocmask`, `sigwait`, `strcmp`, `waitpid`
- Pinned API17 stub audit: every import available; unknown imports: zero.
- Artifact checker: passed.
- Ignored staging copy: mode `0555`, byte-identical; same SHA-256 and MD5.

Source and import inspection found only the bounded diagnostic modes and process/signal support. A raw capability-string scan found only the benign self-test token `LISTENERS=0`; there are no socket/listener imports or calls. The production executable includes no display, framebuffer, SurfaceFlinger, USB/iAP2, MFi, CarPlay, vehicle device path, CAN, HondaHack, or jmcs functionality. Test-only fault modes are compiled into a distinct x86 test binary and are absent from the ARM production artifact.

The direct API17 x86 runtime matrix passed from the shared lifecycle source. That does not establish dynamic loading or runtime on Honda ARMv7. Test A remains unexecuted and separately unauthorized.
