# R7E2 Honda shell command evidence (ECC)

| Command | Preserved observed? | Static Android expectation only? | Needed by A0? | Needed by Test A? | Substitute | Evidence class |
|---|---|---|---|---|---|---|
| `id` | Yes: recorded UID 2000 and fixed 43T0 identity plan uses `shell id` | No | Yes | Optional current recheck | None; stop if missing | HONDA_READ_ONLY_OBSERVED |
| `getprop` | Yes: 43T0 identity capture observed release, SDK, device, board, hardware properties | No | Yes | Identity gate only | None | HONDA_READ_ONLY_OBSERVED |
| `ls` | Yes: corrected 40E used plain `ls`; earlier `-1` unsupported | No | Yes, use `ls -ld` but exact option combination remains not evidenced; if command/options fail, stop | Metadata verification if available | None; no fallback | HONDA_READ_ONLY_OBSERVED, exact `-d` form unproven |
| `cat` | Yes: `/proc/version`, `/proc/mounts` and proc/sys captures | No | Yes | No | SELinux file read only if exists | HONDA_READ_ONLY_OBSERVED |
| `chmod` | No evidence located | API17 toolbox expectation is not enough | No | Possibly, only if separately justified and approved | Prefer artifact's native executable mode/transfer mode only after proven; otherwise blocker | UNPROVEN |
| `rm` | No exact Honda invocation evidence located in allowed ordinary-shell context | Static binary/toolbox presence is insufficient | No | Cleanup if needed | None; no wildcard | UNPROVEN |
| `ps` | Process listings exist in 40E, but exact `ps` invocation is not captured in cited summary | Android utility expectation only | No | Process persistence response | Stop and return partial if unavailable | PARTIAL HONDA_READ_ONLY_OBSERVED |
| `kill` | No ordinary-shell exact invocation observed | Android expectation only | No | Only exact project PID if independently reviewed | No killall/pkill; otherwise rollback blocker | UNPROVEN |
| `sha256sum` | No target utility proof located | Static image presence not established | No | Target hash optional | Host artifact hash + transport record; do not install helper | UNPROVEN |
| `getenforce` | Historical report says unavailable | No | Optional; may be attempted only if explicitly allowed? A0-R plan treats command-not-found as data, no fallback mutation | No | Read `/sys/fs/selinux/enforce` only if present/readable | HONDA_READ_ONLY_OBSERVED (unavailable) |

## ECC command policy

The exact A0-R commands use only the historically evidenced legacy `adb shell` service and fixed identity; all target invocations are proposed with `adb -s <locally-verified-redacted-target> shell ...`, never bare `adb shell`. The exact ls metadata options need output/compatibility caution. Any required command missing or output malformed means stop and return partial evidence. No improvisation or write-capable fallback.

Test A command template must not assume `chmod`, `rm`, `ps`, `kill`, or target hashing. Preserve host-side artifact SHA-256. Do not call Test A rollback ready until exact removal and process disposition are supported by evidence and separately reviewed commands.
