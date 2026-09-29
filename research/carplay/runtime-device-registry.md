# Runtime CarPlay device registry evidence

Date: 2026-09-28. Offline review of saved captures only; no live ADB or vehicle access in this pass.

## Result

**Existing runtime snapshot sufficient: NO.** Existing artifacts identify the owner process, its loaded mappings, and some high-level CarPlay/media log events. None contains the device-manager global/list head, registry nodes, candidate contexts, interface pointers, slot +0 results, or insertion order at mc_dev_attach("CarPlay Screen", ...).

## Existing captures checked

| Capture | What it contains | Why it does not resolve the registry |
|---|---|---|
| research/captures/20260925T150706Z-root-proc-read/ | /proc/16188/maps, status, fd, thread snapshot; captured 2026-09-25 15:28:07 UTC. /system/bin/jmcs is PID 16188 and runs as root. Maps show jmcs and 54 shared-library mappings, including libcarplay_proxy.so, libmedia.so, libstagefright.so, libgui.so, and platform/vendor graphics dependencies. | Maps, thread count, descriptors, and status do not contain process heap/global values or callback tables. Capture does not include /proc/<pid>/mem or a core dump. |
| research/captures/20260925T150706Z-inventory/process-inventory/ | Process list, status and fd snapshots; its /proc/16188/maps read failed with permission denied. | No address-space content; maps failure is recorded in manifest.json. |
| research/captures/20260918T153910Z-native-cluster-readonly/ | Older jmcs maps/status/process snapshots and CarPlay/logcat events. Logs include CarPlay Screen as a named source/storage event and generic media_dev_attach IAP2 callback errors. | The log lines do not show the "CarPlay Screen" manager lookup, callback score, winning registry node, or an address-to-callback relationship. The source/storage name is not proof of device-manager match identity. |
| 2026-09-25 twin/HondaHack and 2026-09-28 display diagnostic captures | Process lists, Android service/display/window state, and filtered logs. | No jmcs heap or registry contents. No device-manager ranking trace. |

The logs are potentially useful context but cannot be promoted to a winner: the media_dev_attach lines are generic callback diagnostics and are not tied by evidence to the exact mc_dev_attach("CarPlay Screen") invocation.

## Runtime owner

- **Registry owner process:** /system/bin/jmcs (confirmed by static function locations and saved process listings/status).
- mc_ScreenStreamStart, mc_dev_attach, devmgr_dev_attach, devmgr_dev_alloc, dev_attach, and dev_attach_to_app are in the jmcs ELF.
- **Expected mappings:** the 2026-09-25 root-readable maps capture lists 54 .so mappings in the same process. Relevant named examples include /system/lib/libcarplay_proxy.so, libmedia.so, libstagefright.so, libgui.so, libui.so, libbinder.so, libcutils.so, and Tegra/NVIDIA libraries. The capture is a historical mapping inventory, not proof that a library supplies the winning interface.
- Saved map bases are ASLR-specific and must not be reused as current addresses.

## Known structure anchor

From the offline jmcs code, the manager's registration-list head is read at manager offset +0x08. Each registry node has next at +0x00 and interface pointer at +0x08; the match and attach function slots are interface +0x00 and +0x04. These are field offsets only. The absolute manager address, current head, node count, and candidate values remain unknown.

## Minimum next observation (not performed)

A short parked observation is required. First collect the already-exposed targeted jmcs log stream and /proc/<pid>/maps/status; neither is expected to expose the heap list. If they do not, a narrowly scoped read-only memory observation is unavoidable: identify the manager global from the offline ELF, read only the manager pointer, list head and node/interface words, then resolve callback addresses against the saved ELF/mappings. Do not attach a mutating debugger, hook code, patch callback tables, or write process/system state. Preserve raw memory only locally and ignored; commit derived addresses and symbol mappings only.

A precise CarPlay Screen match result also requires callback return values. If logs do not expose each score, the read-only observation must capture those return values through a preexisting diagnostic path or a passive execution trace. No such saved trace was found. Do not claim a score based on function names alone.

## Gate

- Existing snapshot sufficient: **NO**.
- Live observation required: **YES**.
- Device-manager address / registry head / entry count: **not available from saved artifacts**.
- Winner / match score / slot +4: **unresolved**.
- Live actions performed in this pass: **none**.
