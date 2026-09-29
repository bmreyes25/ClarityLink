# `jmcs` runtime sockets and module baseline

Date: 2026-09-29. Read-only snapshot with the iPhone disconnected.

## Capture

The process was `/system/bin/jmcs`, PID `26577`, running as root, with load base `0x4008f000`. The iPhone was disconnected throughout. Raw `/proc` metadata and per-FD information are retained locally (ignored by Git) in `research/captures/jmcs-runtime-diff/20260929T160905Z/disconnected/`; its `SHA256SUMS.txt` hashes the captured files.

Socket ownership was established by matching inode numbers from `/proc/26577/fd` symlinks against `/proc/net/tcp`, `/proc/net/tcp6`, and `/proc/net/unix`. The network tables were not treated as process-specific until the inode matched.

## Correlated TCP sockets

| FD | Inode | Local endpoint | Remote endpoint | State | Interpretation |
|---:|---:|---|---|---|---|
| 17 | 257125 | `0.0.0.0:5000` | — | LISTEN | `jmcs` IPv4 listener; ScreenSession role unproven |
| 18 | 257126 | `[::]:5000` | — | LISTEN | `jmcs` IPv6 listener; ScreenSession role unproven |

No `jmcs`-owned established TCP connection appeared in the captured tables. Port `5000` must not be called the screen listener without a code or diagnostic link.

## Correlated Unix sockets

Five `jmcs` socket inodes matched rows in `/proc/net/unix`: `255825` (FD 11), `255826` (FD 12), `258104` (FD 19), `259248` (FD 24), and `259249` (FD 25). The matching rows have no pathname. Other socket FDs did not appear in the captured TCP/TCP6/Unix tables; their type is not inferred here.

## Loaded executable/shared-object paths

`/proc/26577/maps` contains 45 unique mapped `.so` paths, plus `/system/bin/jmcs` and `/system/bin/linker`. The complete derived inventory includes each executable mapping and file offset in [jmcs-module-inventory.md](jmcs-module-inventory.md). The CarPlay/media-related subset is:

| Runtime base | Module | Note |
|---:|---|---|
| `0x4008f000` | `/system/bin/jmcs` | Registry owner and generic registration/attach code |
| `0x40a57000` | `/system/lib/libmedia.so` | Android media framework |
| `0x40529000` | `/system/lib/libstagefright.so` | Android media framework |
| `0x4064e000` | `/system/lib/libgui.so` | Android graphics framework |
| `0x40bb2000` | `/system/lib/libcarplay_proxy.so` | CarPlay screen callback proxy |

Focused offline symbol review confirmed generic `devmgr_app_register` callsites in `jmcs` through `mc_media_dev_register_devmgr` and `mc_iodev_set_cbs`. `libcarplay_proxy.so` does not import `devmgr*` or `dev_attach*`; it is not evidence of a separate device-manager registration producer. This module inventory cannot show the runtime registry nodes, their contexts, insertion order, or callback results.

## Restriction probes

`/proc/26577/status` reports `TracerPid: 0`. `/proc/sys/kernel/yama/ptrace_scope` is absent on this image, and `getenforce` is not installed. These observations do not explain the earlier `/proc/26577/mem` `Operation not permitted` result.

## Result

- Disconnected module and socket baseline: captured.
- Connected snapshot: not required to search the presently identified producers; the CarPlay proxy and media stack are already mapped. A connected `/proc` diff would still not reveal the winner unless a new module appears.
- Screen listener port: unresolved; port `5000` is only a process-owned listener.
- Winning registration / callback: unresolved.
- Live collection for this bounded baseline: complete; car may be turned off.
