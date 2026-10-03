# Step 18 — Runtime registration resolution (offline capture audit)

Date: 2026-09-28
Base: a800af9

## Objective

Check existing ADB/session captures for the runtime device-manager list used by mc_dev_attach("CarPlay Screen", ...) before considering any new live observation.

## Findings

**Existing runtime snapshot sufficient: NO.** The available captures include:

- Root-readable jmcs process metadata and 75 KB /proc/16188/maps captured 2026-09-25 15:28:07 UTC. It identifies /system/bin/jmcs, its mappings, descriptors, status, and threads, but does not include heap/global memory.
- An earlier inventory capture whose /proc/16188/maps read failed with permission denied.
- 2026-09-18 CarPlay logs with high-level named-source events and generic media_dev_attach IAP2 callback diagnostics. They do not tie those diagnostics to the "CarPlay Screen" lookup or expose candidate scores or addresses.
- Other twin, display, service, and log captures without jmcs registry memory.

The maps capture shows 54 .so mappings (including libcarplay_proxy.so, libmedia.so, libstagefright.so, libgui.so, and Tegra/NVIDIA dependencies). This establishes a historical module inventory, not callback provenance. No saved linker map, tombstone, core file, debugger dump, callback table, or device-manager memory snapshot was found in the checked capture classes.

The registry owner is /system/bin/jmcs: mc_ScreenStreamStart, mc_dev_attach, and generic manager functions reside in its ELF. The known list-head field is manager +0x08; absolute manager address and runtime list contents are absent.

## Minimum observation design

First use existing read-only jmcs logs and process metadata/mappings. If these do not expose the registry (as the saved captures do not), the one required observation is a bounded read-only read of the manager pointer, registry head, each node's next and interface pointer, and the first two interface slots, during a CarPlay Screen attach. Resolve addresses offline against jmcs symbols and historical/current mappings. Callback scores must come from an existing diagnostic or passive trace; do not fabricate them. No process writes, hooks, patching, or configuration changes.

## Decision gate

- Existing capture sufficient: **NO**.
- Live observation required: **YES**.
- Runtime address/list/scores/winner/slot +4: **not yet available**.
- Active sink, decoder, Surface, and multi-instance feasibility: **unknown**.
- Display-B readiness: **No**.
- Live work performed during the offline capture audit: **none**.

## Live session result (2026-09-29)

ADB connected at `[REDACTED-PRIVATE-ENDPOINT]:5555`; root succeeded. `pidof` is unavailable; `ps` found `/system/bin/jmcs` PID `26577`. The executable mapping begins at runtime `0x4008f000`, and the process has 45 mapped `.so` files, including `libcarplay_proxy.so`, `libmedia.so`, `libstagefright.so`, and `libgui.so`. The iPhone remained disconnected.

Current `MC`/`MCS` log queries and a targeted term filter returned no lines. DWARF identifies `mc_devs` (static `0x35acbc`, type `devmgr_h`), whose candidate runtime cell is `0x403e9cbc`. A read-only four-byte `/proc/26577/mem` read of that exact cell returned `Operation not permitted`. Therefore the manager pointer and registry head at manager `+0x08` could not be recovered. Registry populated with iPhone disconnected and iPhone requirement both remain **unknown**.

No `gdbserver`, `lldb-server`, or `strace` exists on the head unit. Host LLDB has no target server. `debuggerd` was not invoked because it may write a tombstone; no debugger was attached. No software, settings, callback table, or process memory was changed. The iPhone was not connected.

### Decision gate

- Live vehicle data complete: **NO**.
- Car may be turned off: **YES**; current tools cannot read the manager cell, and no further action is useful while the car remains powered.
- Winner / score / attach callback: **unresolved**.
- Next concrete requirement: an already-available ptrace-capable, read-only memory inspection endpoint that does not write a tombstone or install software. With current tools, the exact four-byte manager-handle read is blocked. Do not connect the iPhone until read access to this cell is available; CarPlay startup cannot resolve the present access restriction.
