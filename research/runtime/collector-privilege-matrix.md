# Step 40E4 — Step 40F privilege matrix

**Scope:** offline review of the Step 40F collector design and the completed Step 40E unprivileged capture. No ADB/device access or collector execution occurred for this review.

## Evidence base

- The Step 40F design is in `tools/honda-readonly-preflight/privileged.py` and `privileged_session.py`. The latter currently has `LIVE_CAPTURE_ENABLED = False` and issues no device command unless enabled; do not treat its fixed-operation plan as an approval to run it.
- The ordinary-shell collector and its allowlist are in `tools/honda-readonly-preflight/collector.py`.
- The 2026-09-29 Step 40E three-phase capture is summarized in [the Step 40E report](../../step-reports/40e-readonly-runtime-preflight.md). Its host bundle is outside Git at `~/CLARITY_RUNTIME_20260929_195051`; the derived inventory is outside Git at `~/CLARITY_RUNTIME_20260929_195051_derived_inventory.json`.
- The inventory reports 1,807 available artifacts; across the three phases, `/proc/<jmcs>/maps`, `smaps`, and `fd` were denied. The phase report independently records those outcomes. The capture SHA table was verified in Step 40E.
- Older root-readable mappings exist for different `jmcs` processes/sessions (for example, PID 16188 on Sep 25 and PID 26577 in the Sep 29 morning snapshot). Their addresses are historical and cannot establish the load bias or free address space of the Step 40E process.

## Datum-by-datum access

“Available unprivileged” below means directly demonstrated by the saved Step 40E capture, not merely expected from Android/Linux. “Required” distinguishes the exact Step 41 runtime-address decision from general confidence-building data.

| Datum | Path/API in collector | Available unprivileged | Root required? | ptrace / target stop? | Offline or saved substitute | Needed for Step 41? |
|---|---|---|---|---|---|---|
| Target/platform identity | `/proc/version`, selected `getprop`, `id`, `ps` | Yes; identity matched in preflight and phase A | No | No | Firmware properties and archived kernel fingerprint corroborate it | No; already established |
| `jmcs` identity, PID, start time, UID/GID, command line | `/proc/<pid>/stat`, `status`, `cmdline`, `ps` | Yes in all three phases; same PID/start identity persisted through the session | No | No | Static ELF hash and old process records only corroborate binary identity, not current process identity | Useful guard; already captured |
| Process state, limits, memory counters, scheduler wait channel | `/proc/<pid>/stat`, `statm`, `status`, `limits`, `wchan`, scheduler leaves | Yes for the ordinary fields in Step 40E | No | No | Some limits/field meanings can be checked against API-17 source; no substitute for live state | No for address calculation; supporting evidence only |
| Process signal masks and status flags | `/proc/<pid>/status` | Yes; process masks available in all phases | No | No | No offline substitute for current mask | Rendezvous planning context only; Step 41 remains blocked on multiple other gates |
| Thread list and thread identity/state/masks | `/proc/<pid>/task`, per-TID `comm`, `status`, `stat`, `wchan` | Yes, mostly. Baseline/post-disconnect had 14 stable observed TIDs; connected phase had 29 readable and transient TIDs, so connected data is partial | No | No | The repeated saved snapshots are usable for observed population; static source cannot recover runtime TIDs | Needed before any future all-thread patch/rendezvous plan, not enough to approve it |
| Address mappings and permissions | `/proc/<pid>/maps` | No; permission denied in baseline, connected, and post-disconnect | The recorded shell UID 2000 cannot read root-owned `jmcs` maps; a privilege boundary or different authorized interface is required | Not intrinsically, but access policy may depend on ptrace eligibility; do not attach merely to bypass it | Old maps prove only their own historical address layouts. ELF `PT_LOAD` data gives static VAs, not current load bias, VMAs, or gaps | **Yes.** Current maps are the principal missing runtime datum |
| Mapping/page metadata | `/proc/<pid>/smaps` (`KernelPageSize`, `MMUPageSize`) | No; permission denied in all three phases | Same as maps | Not intrinsically | `PT_LOAD` alignment, boot-image page field, and 4K-looking addresses are not evidence of live VM page size. No saved matching-session smaps exists | **Yes** for page-size and mapping checks; page size remains unknown |
| Open descriptors and socket attribution | `/proc/<pid>/fd`, symlink targets, optionally `fdinfo` | No; FD directory denied in all phases | Same as maps | Not intrinsically | System-wide `/proc/net/*` tables were captured but cannot attribute rows to `jmcs`; old FD snapshots belong to other process epochs | Helpful for transport diagnosis, not the Step 41 runtime patch address gate |
| Global TCP/UDP/Unix tables | `/proc/net/{tcp,tcp6,udp,udp6,unix}` | Yes in all three phases | No | No | Step 40E contains phase deltas; old tables are historical | Already captured; useful contextual data only |
| Mount options, ASLR, memory and CPU topology | `/proc/mounts`, selected `/proc/sys/*`, `/proc/meminfo`, CPU sysfs | Yes for most selected reads; proc mount showed no `hidepid`, ASLR was 2; cache-index details were not exposed | No | No | Firmware/kernel analysis partially corroborates configuration, but not all current values | No substitute for maps; environment context already collected |
| Kernel config | `/proc/config.gz` | Path returned but the captured legacy-shell bytes did not decompress as the expected gzip stream | No in principle | No | Related Tegra source is not exact Honda config; archived boot/kernel analysis has not recovered exact config | Not required if all mandatory runtime values come from other evidence |
| Display/window state | `dumpsys display`, `SurfaceFlinger`, `window` | Yes; allowed diagnostic commands ran in the 40E session | No | No | Saved display diagnostics exist from other dates; they do not provide process mappings | Not required for Step 41 runtime address derivation |
| Bounded system log tail | `logcat -d -t 500` | Yes; bounded dump captured in the phases | No | No | Existing logs are time-bound and do not substitute for current process mappings | Optional context; not needed for Step 41 |
| Exact live VM page size | No direct confirmed unprivileged interface in this collector | Unknown; `smaps` was denied | Unknown; alternative safe interface not established | No inherent ptrace requirement, but no proven API-17 interface in current allowlist | No valid offline substitute found | **Yes** for the planned memory/veneer model; do not infer from alignment |
| Runtime INFO/SETUP addresses and free veneer gaps | Derived from fresh maps + exact ELF; no target memory read required | No, because maps were denied | Needs readable current maps or a proven equivalent | Does not itself require stopping the process | Old load biases/gaps invalid across process epochs and ASLR | **Yes** for current implementation placement decision |

### Current privilege boundary

The ordinary Step 40E collector uses fixed `adb shell` operations, bounded time/output, an explicit path/operation allowlist, and writes its capture on the host. Its 40E result demonstrates that it can collect identity, process/thread metadata, masks, display diagnostics, logs, CPU/platform data, and global network tables as UID 2000. It also demonstrates the specific limit: process maps, smaps, and FD listings are denied.

The Step 40F privileged design would send a fixed read through `/system/xbin/su -c` and save raw output on the host. “Fixed command” narrows command-injection scope; it does not establish that SuperSU’s invocation, daemon, authorization, or logging path is zero-persistent-write. The risk analysis is in [the privilege threat model](privilege-threat-model.md) and [SuperSU execution path](supersu-execution-path.md).

## Offline recoverability

| Runtime value | Classification | What offline material can establish | What it cannot establish |
|---|---|---|---|
| `jmcs` static callsite VAs, ELF type, load segments, file identity | OFFLINE-RECOVERABLE | Exact analyzed ELF and callsite/static VA relationships | Current runtime address, active mappings or address-space collision |
| API-17 interfaces, ARM syscall ABI, related kernel behavior | PARTIALLY RECOVERABLE | Android source and related Tegra source can constrain likely behavior | Exact vendor kernel implementation/configuration or permission decision |
| Current PID/start token, thread count, masks, phase behavior | RUNTIME-ONLY | Existing Step 40E bundle provides evidence for its captured session | State after process restart or a future CarPlay session |
| Current `jmcs` maps/load bias/permissions/free gaps | RUNTIME-ONLY | Historical captures prove prior layouts; exact ELF verifies mapping arithmetic | The Step 40E process’s current or future map layout |
| Exact target VM page size | RUNTIME-ONLY unless another exact interface is proven | Static alignment and boot format can be explicitly ruled out as proof | Current kernel VM granule |
| Descriptor-to-socket mapping | RUNTIME-ONLY | Global network tables show system-wide endpoints | Which endpoint belongs to `jmcs` without its FDs |

## 40F-Lite recommendation

**Useful unprivileged profile exists, but its collection work was already done in Step 40E.** Step 40E captured the complete no-escalation baseline/connected/post-disconnect profile and demonstrated which values are exposed. Repeating it immediately would add little: it would re-capture identity/thread/display/network observations and hit the same maps/smaps/FD permission boundary. Preserve Step 40E as the 40F-Lite evidence set; do not run another vehicle session just to relabel it.

If a future reason requires a fresh Lite observation, reuse only the ordinary `FixedAdb` path and its reviewed non-root operations. Exclude `PrivilegedRead`, `/system/xbin/su`, upload/exec, `adb root`, ptrace, memory reads, signals, process stop, block devices, mounts, and settings/property writes. The current ordinary collector already has the appropriate fixed read operations; the privileged session is separately disabled. No code change is justified for this profile.

**Outcome:** Step 40F-Lite is READY as a documented, previously captured evidence profile. It does not provide maps/smaps/FDs and therefore does not unblock the specific current-maps/page-size decision required by Step 41. Step 40F remains NOT READY; Step 41 remains NOT READY.

## Decision

- Meaningful unprivileged evidence is available and already collected.
- The Step 40E capture rules out an assumption that all collector data needs root.
- It does not provide the one critical category: a fresh readable `/proc/<jmcs>/maps` plus `smaps` for the intended process epoch.
- Existing offline/runtime records from other sessions are not substitutes for those current mappings.
- No additional unprivileged target collection is recommended until a new decision needs fresh phase deltas. The project should proceed with offline preparation or seek a separately justified and reviewed route to only the blocked procfs reads.
