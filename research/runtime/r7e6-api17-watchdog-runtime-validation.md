# R7E6 API17 watchdog runtime validation

## Result

Decision: `R7E_API17_WATCHDOG_RUNTIME_BLOCKED`.

The API17 x86 diagnostic was **not** executed. This host has a pre-existing shared ADB server that independently attached to each test emulator's local ADB port. Stopping or reconfiguring that shared server was outside this milestone's isolation boundary. The runner's dedicated server remained on its own port and reported no target, so no target command was issued through it. No physical Android device or Honda was contacted.

Two cold boots were stopped before any shell, push, or diagnostic operation. Their private, ignored records are `build/r7e6/runs/api17-runtime-54316acbc602.json` (no emulator transport appeared on the isolated server) and `build/r7e6/runs/api17-runtime-569f6acbc7e6.json` (cancelled after the host's shared server attached). A later isolation probe on port 5586 reproduced the shared-server attachment; its record is `build/r7e6/runs/api17-runtime-57796acbc83d.json`. Each runner cleanup stopped only its owned emulator and private ADB server and removed its unique AVD. Cleanup reported no failures. The runner now checks local socket ownership and stops before any guest command when it sees a foreign ADB owner.

The `--one-device` setting does not isolate emulator transports: current ADB help describes it as a USB-device constraint. Disabling USB enumeration on the private server (`ADB_USB=0`) prevents that server from scanning host USB interfaces, but it cannot prevent a separate already-running ADB server from discovering a loopback emulator. The subsequent unexecuted runner revision now sets `ANDROID_ADB_SERVER_PORT` to the private port and adds an exact-port host-socket ownership guard; this mitigation has not been runtime-validated. Emulator runtime proof therefore remains unestablished. No Test A package or authorization packet is frozen.

## Host and artifact results

- Focused host watchdog tests: 9 passed.
- Full offline suite: 982 passed, 15 skipped; self-locator (3 passed), configured simulator checks, repository health, and whitespace check passed.
- ARMv7 build: NDK r23c `armv7a-linux-androideabi17`, API17; 7,904 bytes.
- SHA-256: `3eecced4b46585b79566d7a17ebd5c692883c83e88db92447128a1e215ade42a`.
- MD5: `b6d64f70999739bc0f180c6cda923342`.
- ELF: ELF32, little-endian, ARM EABI5, PIE; `DT_NEEDED`: `libdl.so`, `libc.so`.
- Imports: `__cxa_atexit`, `__libc_init`, `__errno`, `__sF`, `_exit`, `alarm`, `clock_gettime`, `fflush`, `fork`, `fputs`, `free`, `getpid`, `kill`, `malloc`, `memset`, `nanosleep`, `pause`, `printf`, `puts`, `sigaction`, `sigpending`, `sigprocmask`, `sigwait`, `strcmp`, `waitpid`.
- The checker passed. The ignored staging copy at mode `0555` remains byte-identical (same SHA-256 and MD5). This is an offline artifact audit, not target execution proof.

## Process-lifecycle review

The supervisor's PID comes directly from `fork()`, and it waits only on that PID. An exited but unreaped direct child remains the parent's zombie and its PID is not available for reassignment until reaped; this reasoning applies only to this parent-child relationship. It does not establish safe external PID discovery or recovery.

Host tests cover normal return, child busy-loop and sleep timeouts, parent timeout, crash mapping, inherited `SIGCHLD=SIG_IGN`, fork failure, waitpid error recovery, and repeated child lifecycles. These establish host behavior only. API17 runtime deadlines and cleanup remain unverified.

## Next requirement

Re-run the dedicated API17 AVD with the updated explicit server-port selection and host-socket guard. If the pre-existing server still attaches, use a host arrangement where no shared ADB server can attach, with USB enumeration disabled. Then complete the API17 direct-runtime matrix. Do not treat the present partial boot attempts as passes. Test A remains `NOT_AUTHORIZED`.
