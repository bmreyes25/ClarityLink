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

All operations have a 15-second host timeout and zero retries. The reviewed set has 11 target operations plus one local inventory operation. All target writes are **NONE**. There are no target redirects, pipes, fallback utilities, wildcards, server manipulation, root/elevation, or commands that create, modify, delete, transfer, chmod, or execute files. `no noexec` is reported only as `NO_NOEXEC_FLAG_OBSERVED`, not proof of executable permission.
