# R7E5E Test A process-lifecycle review — offline

**Decision:** `R7E_TEST_A_PROCESS_ROLLBACK_BLOCKED`; Test A remains `NOT_AUTHORIZED`.

## Source-backed Android 4.2.2_r1.2 behavior

The pinned AOSP [`toolbox/ps.c`](https://android.googlesource.com/platform/system/core/+/android-4.2.2_r1.2/toolbox/ps.c) prints the default header:

```text
USER     PID   PPID  VSIZE  RSS   WCHAN    PC         NAME
```

Each process row prints the account name, decimal PID and PPID, numeric memory fields, state/address fields, and then `NAME`. For the leader process, `NAME` is the NUL-terminated first string read from `/proc/<pid>/cmdline` when readable; it falls back to the process name from `/proc/<pid>/stat`. It is not a trustworthy executable-path field in all cases. `ps` optional name filtering is a prefix comparison, so that filter alone cannot prove an exact match.

The pinned AOSP [`toolbox/kill.c`](https://android.googlesource.com/platform/system/core/+/android-4.2.2_r1.2/toolbox/kill.c) defaults to `SIGTERM`; it accepts an optional numeric or named signal after `-`, then applies `atoi` to each remaining argument and invokes `kill(pid, sig)`. Thus a future literal single-PID form would be `/system/bin/kill -9 <positive-decimal-pid>` (one PID argument only), but the source implementation's permissive `atoi` makes strict host-side digit validation mandatory. Do not use `killall`, `pkill`, a name-filtered kill, multiple PID arguments, or a wildcard.

## Honda evidence and blocker

A0-R recorded only metadata presence for `/system/bin/ps` and `/system/bin/kill`; it did not execute either utility, preserve output, or identify the actual Honda toolbox binary. There is no preserved Honda toolbox executable in the reviewed A0-R/A0-WR evidence. The AOSP tag therefore defines a useful expected grammar, not proof of Honda's actual binary or output.

If a future separately reviewed package ever permits recovery, the collector must require the exact expected header and row grammar; a positive decimal PID; `USER=shell`; one and only one row whose `NAME` is exactly the frozen absolute diagnostic invocation string; and no truncation, extra columns, malformed row, duplicate match, or unknown process state. It must stop if the exact invocation string is not exposed (for example if `ps` falls back to a truncated `stat` name), or if output differs from the expected grammar. A unique matching row alone does not eliminate PID reuse between observation and signal delivery; this race also needs a reviewed mitigation. Until actual target behavior and a race-bounded recovery are established, no process kill is authorized or frozen.

## Diagnostic bound

The current `--version` path only prints constants and returns. The self-test performs a fixed 64-byte allocation, one 64-iteration loop, checksum checks, two clock reads, and cleanup; it has no fork, child, thread, daemon, listener, service registration, file, network, display, USB, or vehicle operation. The monotonic reads check ordering only; they do not impose a wall-clock completion bound. R7E5E does not claim a deterministic elapsed-time bound. Any source correction requires a new canonical build, artifact audit, staging copy, collector and manifest identities, and separate authorization review.

