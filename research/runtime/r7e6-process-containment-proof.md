# R7E6 process containment proof status

The diagnostic creates exactly one direct child for each allowed mode. The parent records the PID returned by `fork()`, arms its watchdog, polls/waits only for that PID, and on timeout sends `SIGKILL` to that exact child before waiting for the exact PID. The child arms its own alarm before entering the operation and exits with `_exit()` from its watchdog handler. The signal handler avoids allocation, I/O, locks, and cleanup frameworks. The parent restores default `SIGCHLD` disposition before forking so inherited ignore state cannot auto-reap the child.

The PID-reuse argument is scoped to this direct-child relationship: an exited child that has not been waited on remains a zombie and retains its PID until reaped. This does not generalize to PID values discovered through `ps`, unrelated processes, or external management.

Host fault tests pass, including timeout, crash, fork failure, waitpid recovery, and repeated lifecycles. The test-only modes are excluded from the production build. The ARM/API17 import audit includes the expected process and signal primitives and reports no unknown imports. Runtime timing and behavior on API17 x86 have not been observed, so the full containment claim remains open.

Host ADB command timeout is 12 seconds in the attempted runner, greater than the production internal parent deadline of 4 seconds, but this relationship is only a plan until runtime behavior and a complete isolated route are proven. On any host timeout, the intended policy is stop, preserve evidence, stop only owned emulator processes, and require separate review; no retry, fallback, external `ps`/`kill`, or Test B continuation.
