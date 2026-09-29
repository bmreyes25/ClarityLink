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
- Live actions performed during the offline capture audit: **none**.


## Live read-only attempt (2026-09-29)

ADB to `192.168.86.102:5555` connected; `adb devices -l` reported the Clarity device, and `su -c id` returned root. `pidof` is absent from this head unit, so `ps | grep '[j]mcs'` identified PID **26577**. The iPhone remained disconnected.

| Fact | Live result |
|---|---|
| `jmcs` process | PID `26577`, `/system/bin/jmcs`, root, 20 threads |
| Load base | `0x4008f000` from executable mapping `4008f000-403cf000`, file offset 0 |
| Key mapping | `libcarplay_proxy.so` at `0x40bb2000`; all 45 mapped `.so` paths were enumerated from `/proc/26577/maps` |
| Current debug logs | `logcat -d -s MC MCS` empty; broad read-only filter for `devmgr`, `dev_attach`, `CarPlay Screen`, and device attach/registration terms also returned no lines |
| Registry populated with iPhone disconnected | **UNKNOWN**; runtime manager pointer could not be read |
| iPhone connection required | **UNKNOWN**; no candidate state was visible to establish whether the request registration is present before CarPlay startup |

DWARF identifies global `mc_devs` at static VA `0x35acbc` as `devmgr_h`. Adding the live load base gives the candidate manager-handle cell at runtime address **`0x403e9cbc`**. A read-only four-byte attempt through `/proc/26577/mem` at this exact address failed with `Operation not permitted`; the earlier historical `/proc` mappings remain readable, but process memory is not. The manager pointer, then list head at manager `+0x08`, were therefore not recovered. No raw memory was obtained or retained.

No on-device `gdbserver`, `lldb-server`, or `strace` is available; host `lldb` is present but no target server exists. `debuggerd` exists, but is not suitable for an arbitrary bounded memory read and may create a tombstone; it was not invoked. No software was installed and no debugger attached.

**Live result:** owner and ASLR load base confirmed; registry head, entry count, candidates, scores, winner, and slot `+4` remain unresolved. The car has not been modified; no files or settings were written. The live session can stop and the car may be turned off; no useful next step requires keeping it powered with the current tools.

## Read-only `/proc` differential baseline (2026-09-29)

The iPhone remained disconnected. A second, bounded observation saved only `/proc/26577/maps`, `/proc/26577/status`, `/proc/26577/fd` symlink listing and per-FD `fdinfo`, `/proc/net/{tcp,tcp6,unix}`, plus read-only Yama/SELinux probes. Local files are under the ignored path `research/captures/jmcs-runtime-diff/20260929T160905Z/disconnected/`; `SHA256SUMS.txt` hashes every retained file. No process memory was read, and no debugger, `debuggerd`, ptrace, settings, or head-unit writes were used in this pass.

The process still had PID `26577` and load base `0x4008f000`. It had 45 mapped `.so` paths, including `/system/lib/libcarplay_proxy.so` at `0x40bb2000`, plus `libmedia.so`, `libstagefright.so`, `libgui.so`, and the platform libraries. The captured mapping inventory contains no separate CarPlay device-manager plugin. Focused offline symbol review found the generic `devmgr_app_register` callers in `jmcs` (`mc_media_dev_register_devmgr` and `mc_iodev_set_cbs`). `libcarplay_proxy.so` has no undefined `devmgr*`/`dev_attach*` imports; that module is the screen callback proxy, not evidence of a device-manager registration producer. This inventory identifies the likely code-bearing modules but does not expose which runtime registration nodes they created.

The `jmcs`-owned TCP FDs correlated by socket inode are FD `17` (`0.0.0.0:5000`, LISTEN) and FD `18` (`[::]:5000`, LISTEN). Neither can be attributed to the ScreenSession listener from this evidence. No `jmcs`-owned established TCP socket appeared in the captured tables. Five owned Unix sockets correlated to `/proc/net/unix`; those records have no pathname. The remaining socket FDs did not match rows in the captured TCP/TCP6/Unix tables.

Step 20 statically confirmed that the recovered ScreenSession listener helper binds the caller-supplied port and that the traced ScreenSession setup supplies port 0, then records the assigned port. No static association explains the runtime port-5000 listeners. Their role remains unknown; do not call them the ScreenSession listener or a diagnostic service. The ELF/DWARF audit found no existing read-only devmgr list/dump or per-candidate match log. See [port-5000 audit](port-5000.md), [diagnostic audit](jmcs-diagnostics.md), and [Step 20](../../step-reports/20-jmcs-diagnostic-discovery.md).

The status snapshot reports `TracerPid: 0`. This Android image has no `/proc/sys/kernel/yama/ptrace_scope` path, and `getenforce` is unavailable. The earlier exact `/proc/26577/mem` read denial remains unexplained; these probes do not establish that Yama or SELinux caused it.

### Differential decision

- Disconnected maps/socket baseline: **captured**.
- Separate connected snapshot: **not required for the present offline producer search**. The known CarPlay proxy and media/runtime libraries are already mapped, and the identified device-manager registration entry points are in `jmcs`. A connected maps diff would not reveal the live node pointers or callback results. If a later symbol trace establishes a candidate module that loads only when CarPlay starts, request a connected snapshot then.
- Registration producer candidate: **`jmcs`**, with generic media and I/O registration paths; neither is proven to create the winning `"CarPlay Screen"` entry.
- Screen listener port: **unresolved**. Port `5000` is a `jmcs` listener, but no source evidence ties it to ScreenSession.
- Registry head, entries, match scores, winner, and attach callback: **unresolved**.
- Direct process memory still required: **yes**, unless a pre-existing diagnostic/trace endpoint can expose the exact manager list and match results. Do not retry with a debugger or `debuggerd` as part of this capture.
- Live data collection complete: **yes** for this bounded `/proc` snapshot; **car may be turned off**.
