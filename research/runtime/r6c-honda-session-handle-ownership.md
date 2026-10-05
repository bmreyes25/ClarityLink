# R6C offline handle ownership model

| Handle | Creator / owner | Consumer / close path | Transfer status |
|---|---|---|---|
| USB fd | `jmcs` USB host code, exact open untraced | iAP device code; close untraced | `UNKNOWN` |
| iAP2 device/session | `jmcs` `ios_iap2` layer | iAP2 auth/identification and CarPlay attach; detach symbols exist | Internal only; no external transfer evidenced |
| Auth I²C fd | `os_auth_cp_obtain` in `jmcs` via configured `/dev/i2c-2` | `os_auth_cp_read/write`; `os_auth_cp_release` calls `close` at `0x27c23c` | Process-local; no transfer evidenced |
| Authenticated control socket/security state | `jmcs` AirPlay receiver | request handler/serializer; teardown in same ELF | Exact socket and transfer path `UNKNOWN` |
| Type110 screen socket | `jmcs` screen receiver | ScreenStream, security, teardown | Internal; see [R3B](43t1-r3b-lifecycle-cleanup-static-closure.md) |
| Type111 screen socket | no accepted Honda path established | none | `UNKNOWN` |
| Audio channel | `jmcs` AirPlay/audio callbacks and Android media | close path incompletely traced | Separate reuse `UNKNOWN` |
| Input/control channel | `jmcs` iAP/HID and CarPlay interface callbacks | close path incompletely traced | Separate reuse `UNKNOWN` |

This model is architectural. It contains no descriptor duplication, process access, or deployment procedure. A session association or transfer must be proven before any adapter may consume a factory handle.
