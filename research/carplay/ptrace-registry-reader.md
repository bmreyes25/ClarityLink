# Bounded ptrace registry reader

This is an offline-only implementation and audit record. It does not authorize or perform a vehicle run. Full ABI, tests, risk assessment, and future procedure are in [Step 24](../../step-reports/24-ptrace-registry-reader.md).

## Behavior

The C utility at `research/tools/jmcs_ptrace_registry_reader/reader.c` accepts a current PID and a freshly computed `mc_devs` cell. It confirms `/proc/PID/cmdline` is exactly `/system/bin/jmcs`, parses readable mappings before attaching, then uses only `PTRACE_ATTACH`, `waitpid`, bounded `PTRACE_PEEKDATA`, and `PTRACE_DETACH`. JSON is emitted only after a successful detach. The iPhone must be disconnected for any future separately reviewed attempt.

The ptrace attachment stops one task, not every thread in `jmcs`. Two identical walks are required, capped at 128 nodes and 5,136 target bytes total. This is a race detector, not an atomic process snapshot. Any read failure, invalid pointer, cycle, excessive list, wait failure, signal interruption, or inconsistent pass aborts through the single detach cleanup path. Detach is attempted once; failure prints `CRITICAL_DETACH_FAILURE` and the program exits without retry.

## Build and test

```sh
cd research/tools/jmcs_ptrace_registry_reader
make test
NDK_ROOT='/Volumes/Android NDK r23c/AndroidNDK8568313.app/Contents/NDK' make armv7
shasum -a 256 jmcs_ptrace_registry_reader
```

NDK r23c, API 17, `armv7a-linux-androideabi17`. Audited binary SHA-256: `1fa1fc980637af5c586b0897ef46ae8c5639c12ac5028ff8d3d0a76e7b672bad`. No emulator or vehicle execution.

**READY FOR CAR: NO.** A live attach requires review of the single-thread pause, signal race, non-atomic snapshot, and detach-failure limits. Do not retry `process_vm_readv`; its one live attempt returned `ENOSYS`.
