# Step 19 — Read-only `jmcs` `/proc` differential baseline

Date: 2026-09-29 16:09 UTC

## Objective

Use the least invasive disconnected-state observation to identify modules that may produce the runtime `"CarPlay Screen"` device registration and correlate `jmcs` sockets by inode. Do not attach a debugger or read process memory.

## Findings

- ADB/root remained available; `/system/bin/jmcs` was PID `26577`, base `0x4008f000`. The iPhone remained disconnected.
- Captured `/proc/26577/maps`, `status`, FD links and all readable `fdinfo` files, `/proc/net/tcp`, `tcp6`, `unix`, and read-only Yama/SELinux probes. The local capture is ignored by Git and has a SHA-256 manifest.
- The process had 45 `.so` paths mapped, including `libcarplay_proxy.so`, `libmedia.so`, `libstagefright.so`, and `libgui.so`. The current module inventory contains no separate CarPlay device-manager plugin.
- The `jmcs` ELF has the known generic registration entry points and direct `devmgr_app_register` routes through `mc_media_dev_register_devmgr` and `mc_iodev_set_cbs`. `libcarplay_proxy.so` has no `devmgr*`/`dev_attach*` imports. Its presence does not identify the winning device-manager entry.
- Only TCP FDs 17 and 18 matched `jmcs` socket inodes: `0.0.0.0:5000` and `[::]:5000`, both LISTEN. Their ScreenSession role is unproven. No owned established TCP connection was observed.
- Five owned Unix socket inodes matched `/proc/net/unix`; their rows had no pathname.
- Status reports `TracerPid: 0`; Yama `ptrace_scope` is absent and `getenforce` is unavailable. The previous `/proc/<pid>/mem` denial's cause remains unknown.

## Decision

A connected maps diff is **not currently needed** for the identified producer search: known CarPlay, media, and graphics modules are already present, and the manager registration callsites are in `jmcs`. It would not expose the runtime list. If later offline evidence names a candidate module loaded only at CarPlay startup, request a connected snapshot then.

The read-only disconnected `/proc` collection is complete; the car may be turned off. The listener role, manager/list head, candidate entries, scores, winning registration, slot `+4`, sink, decoder, and Surface remain unresolved. The exact winner still requires runtime list/match evidence or a pre-existing diagnostic path. No debugger, `debuggerd`, ptrace, process write, firmware modification, or connected phone was used in this step.

## Evidence

- [Runtime registry evidence](../research/carplay/runtime-device-registry.md)
- [Correlated sockets and loaded-module baseline](../research/carplay/jmcs-runtime-sockets.md)
- [Complete executable-module inventory](../research/carplay/jmcs-module-inventory.md)
- Local ignored capture: `research/captures/jmcs-runtime-diff/20260929T160905Z/disconnected/`
