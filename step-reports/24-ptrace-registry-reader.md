# Step 24 — bounded ptrace registry reader (offline only)

Date: 2026-09-29. No vehicle, ADB, `jmcs`, debuggerd, firmware, or live process was used in this milestone.

## Result

A minimal C reader and synthetic ptrace backend were implemented in `research/tools/jmcs_ptrace_registry_reader/`. The ARM binary is built from this source with official NDK r23c (23.2.8568313), API 17, target `armv7a-linux-androideabi17`. The native synthetic suite passes. No ARM emulator was used. The reviewed binary SHA-256 is `1fa1fc980637af5c586b0897ef46ae8c5639c12ac5028ff8d3d0a76e7b672bad`.

The allowed target ptrace requests are exactly `PTRACE_ATTACH=16`, `PTRACE_PEEKDATA=2`, and `PTRACE_DETACH=17`, from the NDK r23c sysroot `usr/include/linux/ptrace.h` included by `usr/include/sys/ptrace.h`. Header values were verified locally against the exact NDK used to build. Android 4.2.2 Bionic's `ptrace.c` handles PEEK requests by returning the peeked word and relies on errno to distinguish an error, so code clears errno before PEEK and treats `-1, errno==0` as valid `0xffffffff` data. Sources: NDK r23c `sysroot/usr/include/linux/ptrace.h` (local verified toolchain), [Android 4.2.2 Bionic ptrace wrapper](https://android.googlesource.com/platform/bionic/%2B/a27d2baa0c1a2ec70f47ea9199b1dd6762c8a349/libc/bionic/ptrace.c), [Linux ptrace(2)](https://man7.org/linux/man-pages/man2/ptrace.2.html).

`PTRACE_ATTACH` targets a single task/TID, requests SIGSTOP, and can return before the task has stopped. The reader waits with `waitpid(pid, ..., 0)` and requires the same PID plus `WIFSTOPPED`; it expects the attach SIGSTOP. `PTRACE_DETACH` is the restart operation. It passes signal 0 to suppress the attach-generated SIGSTOP and resume the task. If another signal-delivery stop is observed first, it aborts and forwards only that already-observed signal on detach; it synthesizes no signal. SIGINT/SIGTERM handlers only set a flag. After attach, EINTR during wait is retried until stop confirmation; the flag then routes through cleanup. All ordinary post-attach outcomes converge on one cleanup call and exactly one detach attempt. A detach error emits `CRITICAL_DETACH_FAILURE`, exits immediately, and is not retried. Tracer death generally auto-detaches and restarts tracees in Linux documentation, with group-stop caveats; the exact vendor-kernel failure behavior is not proven. This is an unavoidable residual risk, not a tested guarantee.

Ptrace attachment is per task, not process-wide. Attaching to the `jmcs` leader is sufficient to read its shared virtual address space, so `THREAD ATTACH REQUIRED: NO` for address access. Other `jmcs` threads continue running. Two bounded traversals are therefore retained and must compare exactly; this detects observed changes but cannot prove an atomic process-wide snapshot (an ABA mutation can evade comparison). The design does not attach every thread. Maximum target reads are `2 * (2 + 5*128) * 4 = 5,136` bytes (1,284 PEEK requests). It walks only the known cell -> manager -> `+0x08` head -> node (`+0`, `+4`, `+8`) -> interface (`+0`, `+4`) chain, never dereferences bookkeeping, caps at 128, checks readable mappings/alignment and loops, and prints the minimal JSON only after successful detach.

## Audit

- ABI constants: verified from exact NDK r23c `linux/ptrace.h`; built calls use only attach/peek/detach.
- ELF: ELF32, little-endian, ARM, EABI5, PIE/DYN, interpreter `/system/bin/linker`, entry `0x1a84`.
- DT_NEEDED: `libdl.so`, `libc.so`; both exist in saved forensic firmware.
- Undefined imports: `ptrace`, `waitpid`, `clock_gettime`, `sigaction`, stdio/file/string/parsing functions and Bionic startup symbols. Each was checked against the saved firmware `libc.so`/`libdl.so`; all exist. No newer versioned API requirement was found.
- ISA attributes: ARMv7 application profile; disassembly is ARM/Thumb-2 compatible code, no ARMv8 instructions observed. `-mfloat-abi=softfp` used; reader has no SIMD requirement.
- Source safety: no POKEDATA/POKETEXT/SETREGS/CONT/SINGLESTEP/SYSCALL, process_vm access, `/proc/PID/mem`, kill/raise, debuggerd, breakpoint, or register-modification path. No target-memory writes or register writes. One ordinary signal observed at a ptrace stop may be forwarded unchanged; no signal is fabricated.
- Synthetic scenarios pass: attach EPERM, attach success, wait failure, invalid pointer, first and mid-list PEEK errors, loop, >128 entries, 128-entry valid list, `-1` with errno clear/set, unexpected stops, detach success/failure, and exactly one detach attempt after every successful attach.
- Synthetic command: `make test`.
- ARM command: `NDK_ROOT='/Volumes/Android NDK r23c/AndroidNDK8568313.app/Contents/NDK' make armv7`.
- Binary SHA-256: `1fa1fc980637af5c586b0897ef46ae8c5639c12ac5028ff8d3d0a76e7b672bad`.

## Live risk and gate

Expected pause is the duration of attach/wait, at most 1,284 word peeks, and detach; duration is measured with `CLOCK_MONOTONIC` and emitted only in successful JSON. The main failure risk is failure to detach after attach (reported critical; process exit is expected to trigger kernel cleanup, but this vendor-kernel behavior is not directly established), followed by sibling-thread mutation or an unexpected signal race. No target writes, register writes, breakpoints, callback execution, or persistence are present.

**READY FOR ONE PARKED TEST: NO, pending review of the single-thread stop/signal/detach failure limits and the non-atomic snapshot caveat.** This milestone was explicitly offline-only; no test was run on the car. A future trial must be separately requested/reviewed and must verify detach plus same PID/cmdline immediately afterward. No automatic retry.

## Future procedure (prepared, not executed)

1. With iPhone disconnected and only during a separately authorized parked session, connect ADB, verify `su -c id` is root, list `jmcs`, select current PID, and verify `/proc/PID/cmdline` equals `/system/bin/jmcs`.
2. Capture current `/proc/PID/maps`; use the offline ELF helper to recompute load bias and `mc_devs` cell. Never reuse historic PID/base/cell.
3. Verify local reader SHA-256 exactly equals the hash above; only then push one reader executable to `/data/local/tmp`, `chmod 700` it.
4. Run once with `--pid PID --mc-devs-cell CELL`, capturing stdout/stderr on the Mac. Do not connect the iPhone. Accept only JSON with `attach_succeeded`, `wait_succeeded`, and `detach_succeeded` true; `CRITICAL_DETACH_FAILURE` means stop immediately.
5. Immediately re-read the same PID cmdline and process list; confirm that exact PID remains `/system/bin/jmcs`. Remove the remote executable, disconnect ADB, and turn the car off. No retry after any reader/kernel/permission/consistency result.

## Go/no-go

- Ptrace reader: IMPLEMENTED
- ARMv7 build: PASS
- Ptrace ABI: VERIFIED (NDK headers; legacy Bionic semantics verified)
- Allowed requests: ATTACH, PEEKDATA, DETACH
- Target memory writes: NONE
- Target register writes: NONE
- Expected pause: one `jmcs` task, while sibling threads continue
- Detach safety tests: PASS for exactly-one detach attempt on all tested post-attach paths; runtime resume guarantee after detach failure is not proven
- Safety audit: PASS for scoped source/build; disclosed ptrace stop and signal-forwarding semantics
- Synthetic tests: PASS
- Ready for car: NO
- Blocker: review/acceptance of thread-level stop, signal race, and detach-failure limits before any live attach
