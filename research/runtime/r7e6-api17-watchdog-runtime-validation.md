# R7E6 API17 watchdog runtime validation

## Result

Runtime decision: `ANDROID_API17_X86_RUNTIME_WATCHDOG_PROVEN_X86`.

The final run used a unique project-owned AVD (`r7e6_api17_69ad6acbcd28`), exact emulator serial `emulator-5580`, and a dedicated ADB server on port 5038. The guest identified as Android 4.2.2, API17, x86, and Dalvik 1.6.0. `ADB_USB=0` disabled USB enumeration on the private server. Host socket ownership checks found only the owned emulator and private server on the emulator ADB port. Every ADB target command used that exact server and serial. No physical Android device or Honda was contacted.

Final private evidence is `build/r7e6/runs/api17-runtime-69ad6acbcd28.json`, SHA-256 `297e1dd98b93947a7e1595a7d48474c56f618f9f6ed544305ec7f8d84bf3a71c`. It records 213 diagnostic invocations, all runtime results and exact PID observations, and 100 completed version/self-test pairs. The runner stopped only its owned emulator/private server, removed the run-specific AVD, and reported no cleanup failures. It does not retain raw remote `ls`/MD5 output; the assertions for regular-file mode, owner, group, size, and MD5 passed before any diagnostic mode ran.

Early failed attempts are retained as ignored local evidence. They exposed the shared-server conflict, an incorrect emulator-console identity query, ADB push progress on stderr, emulator `root:root` ownership, the `ls` basename format, and inherited ignored `SIGSEGV` in the test-only crash mode. The runner/test variant was corrected and rerun; the passing result is from the final run above.

## Runtime results

- `--version`: five initial invocations and 100/100 repeated invocations returned 0 and exact child-reaped records.
- `--self-test`: initial invocation and 100/100 repeated invocations returned 0, reported `SELF_TEST_PASS` and `RESOURCE_COUNTS final=0`, and emitted exact child-reaped records.
- Child busy loop: watchdog status 124; child reaped; exact child PID absent afterward.
- Child blocked sleep: watchdog status 124; child reaped; exact child PID absent afterward.
- Test-only child crash: status 126 after explicitly restoring `SIGSEGV` default; exact child reaped.
- Ignored inherited `SIGCHLD`: reset and exact wait succeeded.
- Injected fork failure: deterministic status 127; no child reported.
- Injected waitpid error: exact child termination/reap recovery; status 127.
- Parent watchdog: status 125; exact child and parent PIDs absent after completion.
- 100 repeated version/self-test pairs: 100 completed. Maximum observed pair duration 1.9353 s; self-test 1.3013 s; initial version samples min/median/max 0.8072/1.0969/1.4390 s.
- Host command timeout: 12 s. Production internal parent bound: 4 s; child bound: 2 s.

The emulator's pushed test artifact had mode `0555`, owner/group `root:root`, and exact local size/hash/MD5 assertions passed. The root ownership belongs to this emulator image; Honda Test A still requires `shell:shell`.

## Build and import audit

The rebuilt ARMv7 target is 7,904 bytes, SHA-256 `9e20d1ad715be6c9974f9a89e1aa310283bc128f87350fb05cb224b8e247c063`, MD5 `6137a693a77646aaf9a4cf0f351731d4`. ELF is 32-bit little-endian ARM EABI5 PIE with only `libdl.so` and `libc.so` needed. Pinned API17 NDK stubs classify every import as available; unknown imports: zero. The ignored staging copy is byte-identical at mode `0555`.

The separate test-only API17 x86 fault binary is SHA-256 `1df178f499f50fe5efdf1a782e3898e16541d03b8ec2423b12e4572ba2c12247`; it is not the Honda artifact and is never staged by the Test A collector.

## Limits

This proves the shared source's process lifecycle on an API17 x86 emulator, not ARMv7 execution on the Honda or behavior under Honda-specific kernel/loader conditions. It does not establish any display, USB, MFi, iAP2, CarPlay, or vehicle capability. The separate Test A collector and package have their own hash-bound authorization gate; Test A remains `NOT_AUTHORIZED`.
