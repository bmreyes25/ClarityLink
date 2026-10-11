# R7E5F self-bounded diagnostic design

**Status:** offline implementation reviewed; host proof complete; API17 x86 emulator runtime proof not performed. **Test A:** not authorized.

## Architecture

`--version` and `--self-test` enter one common supervisor. The parent arms a four-second `SIGALRM` deadline before `fork()`, blocks the alarm across fork/PID publication, stores the exact returned child PID, then performs bounded `waitpid(child_pid, ..., WNOHANG)` polling. The child installs a `SIGALRM` handler whose sole action is `_exit(124)`, unblocks the signal, arms its two-second alarm before starting the requested operation, flushes bounded output, disarms the timer, and `_exit`s with the operation status. A parent timeout handler uses `kill(exact_child_pid, SIGKILL)`, waits for that exact child, then `_exit(125)`. These are libc process primitives controlling only the direct child; no toolbox process discovery or kill is in the normal plan.

The parent blocks `SIGALRM` while observing/reaping a completed child, disarms its alarm, consumes any pending alarm, clears the published PID, and only then restores the signal mask. This prevents a delayed parent alarm from targeting a PID after the child has been reaped and its PID could be reused. On timeout, the child remains the parent's unreaped child until the parent has killed and reaped it. This reasoning applies only to this direct-child relationship; it does not establish safe name-based management of unrelated processes.

The signal handlers do no allocation, stdio, locking, logging, or cleanup-framework work. The child handler calls only `_exit`; the parent handler uses `kill`, `waitpid`, and `_exit`. Requested operations are bounded: version emits constants; self-test allocates 64 bytes, executes a fixed 64-iteration checksum/invariant pass, checks monotonic-clock ordering, frees the allocation, and emits bounded output. No child process, thread, listener, service, device, display, USB, network, Binder, or vehicle API is created by either operation.

Production watchdogs are child 2 seconds and parent 4 seconds. Test builds use shorter deadlines and compile-time-only fault modes unavailable in production. Host measured normal invocations complete under one second; timeout cases return under three seconds. These timings are host evidence, not API17 or Honda proof. Any future host collector timeout must exceed the four-second internal parent deadline plus an independently justified transport/scheduling grace.

## Evidence classes

- `DOCUMENTED_API17_OR_ERA_BEHAVIOR`: API17-era POSIX/Bionic interfaces and the pinned NDK r23c API17 stubs expose the required `fork`, `waitpid`, `kill`, `sigaction`, `alarm`, `nanosleep`, `clock_gettime`, and `_exit` interfaces. This is documentation/header evidence, not runtime evidence.
- `HOST_RUNTIME_PROOF`: host-native normal, fault-injection, repeated lifecycle tests passed; see `tests/native/test_r7e1_target_diag_watchdog.py`.
- `API17_EMULATOR_RUNTIME_PROOF`: **not established**. Running the project's Android 4.2.2/API17 emulator test path requires ADB. R7E5F explicitly prohibits ADB, so this gate remains open.
- Honda runtime proof: **not established** and not implied by any evidence above.

No production `--hang` mode exists. `CLARITYLINK_TEST_FAULTS` adds test-only child-loop, sleep, crash, and parent-timeout modes and is not defined for the ARM production build.
