# R7E3 A0-R command manifest (ECC)

Canonical machine-readable manifest: [r7e3-a0r-plan-manifest.json](r7e3-a0r-plan-manifest.json). SHA-256 is published in the readiness decision and authorization packet. Each target command below is executed as `adb -s "$TARGET" <fixed argv>`; no dynamic command string is built.

| ID | Exact command template | Read | Write | Process / privilege | Persistence / side effect |
|---|---|---|---|---|---|
| A0R-00 | `adb devices` | Host inventory | None | Host client only | No target invocation; do not start/kill/reconnect server |
| A0R-01 | `adb -s "$TARGET" shell id` | UID/GID/groups | None | Transient shell + id; ordinary shell | None; UID other than 2000 stops |
| A0R-02 | `adb -s "$TARGET" shell getprop ro.build.version.release` | Release | None | Transient shell + getprop | None; require 4.2.2 |
| A0R-03 | `adb -s "$TARGET" shell getprop ro.build.version.sdk` | SDK | None | Transient shell + getprop | None; require 17 |
| A0R-04 | `adb -s "$TARGET" shell getprop ro.product.cpu.abi` | ABI | None | Transient shell + getprop | None; require ARMv7-compatible ABI |
| A0R-05 | `adb -s "$TARGET" shell pwd` | cwd | None | Transient shell | None |
| A0R-06 | `adb -s "$TARGET" shell ls -ld /data` | path metadata | None | Transient shell + ls | None; exact option failure stops |
| A0R-07 | `adb -s "$TARGET" shell ls -ld /data/local` | path metadata | None | Transient shell + ls | None; exact option failure stops |
| A0R-08 | `adb -s "$TARGET" shell ls -ld /data/local/tmp` | path metadata | None | Transient shell + ls | None; failure = `LS_LD_UNAVAILABLE`, destination section stops |
| A0R-09 | `adb -s "$TARGET" shell cat /proc/mounts` | complete mount table | None | Transient shell + cat | None; noexec on /data blocks |
| A0R-10 | `adb -s "$TARGET" shell cat /proc/self/status` | process status | None | Transient shell + cat | None |
| A0R-11 | `adb -s "$TARGET" shell cat /sys/fs/selinux/enforce` | visible SELinux value | None | Transient shell + cat | None; unreadable = `SELINUX_STATE_UNAVAILABLE` |
| A0R-12 | `adb -s "$TARGET" shell ls -l /system/bin/toolbox` | literal tool metadata | None | Transient shell + ls | None; record TOOLBOX_PRESENT or TOOLBOX_UNAVAILABLE; never execute inspected tool |
| A0R-13 | `adb -s "$TARGET" shell ls -l /system/bin/rm` | literal tool metadata | None | Transient shell + ls | None; record RM_PRESENT or RM_UNAVAILABLE; never execute inspected tool |
| A0R-14 | `adb -s "$TARGET" shell ls -l /system/bin/ps` | literal tool metadata | None | Transient shell + ls | None; record PS_PRESENT or PS_UNAVAILABLE; never execute inspected tool |
| A0R-15 | `adb -s "$TARGET" shell ls -l /system/bin/kill` | literal tool metadata | None | Transient shell + ls | None; record KILL_PRESENT or KILL_UNAVAILABLE; never execute inspected tool |
| A0R-16 | `adb -s "$TARGET" shell ls -l /system/bin/md5` | literal tool metadata | None | Transient shell + ls | None; record MD5_PRESENT or MD5_UNAVAILABLE; never execute inspected tool |
| A0R-17 | `adb -s "$TARGET" shell ls -l /system/bin/chmod` | literal tool metadata | None | Transient shell + ls | None; record CHMOD_PRESENT or CHMOD_UNAVAILABLE; never execute inspected tool |

All operations have a 15-second host timeout and zero retries. The reviewed set has 17 target operations plus one local inventory operation. All target writes are **NONE**. There are no target redirects, pipes, fallback utilities, wildcards, server manipulation, root/elevation, or commands that create, modify, delete, transfer, chmod, or execute files. `no noexec` is reported only as `NO_NOEXEC_FLAG_OBSERVED`, not proof of executable permission.

## R7E4 research-backed refinement (offline only)

Prior manifest SHA-256 `5b73badc219e87ef41eebb154ed4875c0c3ec2e3b19c61f2f2dc5209f3ff963e` is `SUPERSEDED_BEFORE_AUTHORIZATION`; no authorization was granted under it. The normalized manifest at [r7e3-a0r-plan-manifest.json](r7e3-a0r-plan-manifest.json) now carries plan version `R7E4-A0R-COMMAND-SET-1` and SHA-256 `962b25fca36dabde11f2406da1e5d898a0fe5c3a49f78f2bd00f292910442004`. Its six added A0-R commands are fixed `ls -l` metadata reads for `/system/bin/toolbox`, `rm`, `ps`, `kill`, `md5`, and `chmod`; none executes those tools. Missing tool entries are recorded as `<TOOL>_UNAVAILABLE` and remain informational for A0-R; missing `rm`, `ps`, or `kill` also records a separate future-plan review blocker, while missing optional `md5` or unnecessary-by-default `chmod` does not block A0-R. `SELINUX_STATE_UNAVAILABLE` is informational and is never interpreted as disabled or permissive. `/data` `noexec` remains a hard blocker.

For future Test A, require host artifact mode `0755` before transfer, then verify the remote mode with `ls -l`; if the target executable bit is absent, stop without automatic `chmod`. SHA-256 remains the canonical identity; MD5 is optional transport consistency only. A0-W is proposed as one unique inert `0644` marker pushed through ADB sync, read-only inspected and optionally MD5-compared, then removed by exact path with a proven `rm`; it remains separately unauthorized and must not auto-run. See [R7E4 Android 4.2.2 research](r7e4-android42-target-path-research.md).
