# TEST A0 — target environment preflight / A0-R (ECC)

**Status:** `READY_FOR_SEPARATE_TEST_A0_READONLY_AUTHORIZATION` only. Not executed. **Risk:** Tier 1, `HONDA_READ_ONLY`. A0-R authorization does not authorize A0-W or Test A.

## Objective and safety envelope

Record ordinary shell identity; API/build/ABI; candidate `/data/local/tmp` existence, owner and mode; relevant mount flags; visible SELinux state; and exact operator-observed vehicle condition. No file create, chmod, push, execution, display activity, service change, process kill, USB/iAP2, MFi, or CarPlay. Host capture only. ECC reviewed each command for read-only behavior.

## Operator gate before any target operation

1. In a stationary, safely parked location, record the directly observed power mode (use the vehicle's displayed/control terminology; never infer from ADB), parking state, center display fully booted, cluster normal, and no unexpected warnings. Stop if any condition is not met.
2. Verify host `adb devices` shows exactly one intended Honda target in `device` state. If zero or multiple, STOP. Record its identity only in a local, access-controlled, redacted evidence record; do not commit serial/IP. Resolve and pin that exact identity for every operation. No scanning/retry/troubleshooting.
3. If host target identity cannot be unambiguously validated, no target command runs.

## Proposed commands (NOT EXECUTED; proposed A0-R only)

`<TARGET>` is an operator-verified local variable, never a literal placeholder in a runnable script. Each command uses the explicit selector:

```sh
adb devices
adb -s "$TARGET" shell id
adb -s "$TARGET" shell getprop ro.build.version.release
adb -s "$TARGET" shell getprop ro.build.version.sdk
adb -s "$TARGET" shell getprop ro.product.cpu.abi
adb -s "$TARGET" shell pwd
adb -s "$TARGET" shell ls -ld /data
adb -s "$TARGET" shell ls -ld /data/local
adb -s "$TARGET" shell ls -ld /data/local/tmp
adb -s "$TARGET" shell cat /proc/mounts
adb -s "$TARGET" shell cat /proc/self/status
adb -s "$TARGET" shell cat /sys/fs/selinux/enforce
```

`adb devices`, `id`, `getprop`, `pwd`, `cat`, and legacy `adb shell` have historical evidence. `ls -ld` exact compatibility has not been directly observed; use only if the fixed command returns expected directory metadata, otherwise stop; no alternate options. The SELinux file may not exist/read; report unavailable, do not infer disabled. Historical `getenforce` was unavailable, so it is not in the command list. Commands are observations only; stdout/stderr and exit status are captured to host with target identity redacted. The `/proc/mounts` read is broad but read-only and needed for the current `/data` line.

## Stop conditions

Unexpected reboot, UI freeze, cluster behavior change, center-display loss, unexpected privilege prompt/elevation, any mutation, required command missing, malformed/unexpected output, destination mismatch, SELinux/mount evidence contradicting plan, multiple/ambiguous targets, or any departure from the fixed command list. No improvisation. Stop and record partial output.

## Success and limits

Success records shell UID/GID/groups; platform identity; directory metadata; `/data` mount flags; SELinux observation or explicit unavailable result; exact observed parked/power state; and stock UI/cluster observation. It does not prove write/delete, executable mapping, or execution. If write/delete remain unknown, A0-W is proposed separately and must be separately authorized. Test A remains unapproved pending review of A0-R results, exact commands and rollback.

## Command audit

All commands read target properties/files/metadata; writes: **NONE**; target process: existing shell only; privilege: ordinary shell; expected outcome: bounded textual observation. Host evidence capture is a host write. Failure: stop with partial evidence. No target rollback is needed or expected.

## R7E4 research-backed refinement (offline only)

The prior manifest SHA-256 `5b73badc219e87ef41eebb154ed4875c0c3ec2e3b19c61f2f2dc5209f3ff963e` is `SUPERSEDED_BEFORE_AUTHORIZATION`; no authorization was granted under it. The normalized manifest at [r7e3-a0r-plan-manifest.json](r7e3-a0r-plan-manifest.json) now carries plan version `R7E4-A0R-COMMAND-SET-1` and SHA-256 `962b25fca36dabde11f2406da1e5d898a0fe5c3a49f78f2bd00f292910442004`. Its six added A0-R commands are fixed `ls -l` metadata reads for `/system/bin/toolbox`, `rm`, `ps`, `kill`, `md5`, and `chmod`; none executes those tools. Missing tool entries are recorded as `<TOOL>_UNAVAILABLE` and remain informational for A0-R; missing `rm`, `ps`, or `kill` also records a separate future-plan review blocker, while missing optional `md5` or unnecessary-by-default `chmod` does not block A0-R. `SELINUX_STATE_UNAVAILABLE` is informational and is never interpreted as disabled or permissive. `/data` `noexec` remains a hard blocker.

For future Test A, require host artifact mode `0755` before transfer, then verify the remote mode with `ls -l`; if the target executable bit is absent, stop without automatic `chmod`. SHA-256 remains the canonical identity; MD5 is optional transport consistency only. A0-W is proposed as one unique inert `0644` marker pushed through ADB sync, read-only inspected and optionally MD5-compared, then removed by exact path with a proven `rm`; it remains separately unauthorized and must not auto-run. See [R7E4 Android 4.2.2 research](r7e4-android42-target-path-research.md).
