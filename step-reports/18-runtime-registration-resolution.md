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
- Live work performed: **none**.

**Action required before any live work:** Park and power the Clarity, reconnect ADB, and reply READY.
