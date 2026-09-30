# Step 40F-Lite — unprivileged runtime evidence profile

**Status: PROFILE READY; equivalent three-phase collection ALREADY COMPLETED as Step 40E.** This note is a design/reassessment only. No live command, ADB connection, or collector execution occurred for this review. The car does not need to be brought back for a duplicate Lite capture.

## Purpose

Preserve useful runtime evidence from ordinary UID-2000 `adb shell` reads without invoking `su`, enabling `adb root`, attaching to or stopping `jmcs`, or writing to the target. This profile answers whether process identity/lifecycle, thread population, signal masks, display state, and global network state change across stock CarPlay phases.

It does not bypass the demonstrated read restrictions on `/proc/<jmcs>/maps`, `smaps`, or `fd`.

## Evidence already collected

The Step 40E host collector completed baseline (iPhone disconnected), stock CarPlay connected, and post-disconnect phases. The raw bundle `~/CLARITY_RUNTIME_20260929_195051` is outside Git. The host-side report [40E](../../step-reports/40e-readonly-runtime-preflight.md) records the result; its SHA-256 table had zero mismatches.

| Evidence item | Observed availability | Value for the present blocker | Required for Type111 negotiation? |
|---|---|---|---|
| Target identity (`/proc/version`, selected read-only properties, shell UID) | Available; exact platform fingerprint matched | Confirms target identity and shell boundary | No; already established |
| `jmcs` process identity (PID, start time, cmdline, UID/GID, status) | Available in each phase; same process identity across this session | Validates process continuity and avoids mistaking restart for a phase delta | Useful guard, not sufficient for current map addresses |
| Thread listing/status/stat/wchan and signal masks | Mostly available; stable baseline and post-disconnect sets, partial connected samples due to short-lived TIDs | Documents thread growth and signals before any future rendezvous design | No for negotiation-only; required context before any runtime patching |
| `/proc/<jmcs>/maps` | Permission denied in all three phases | **Critical missing item:** runtime load bias, mapping permissions, and actual gaps | Not a negotiation-only prerequisite, but required by current Step 41 implementation gate |
| `/proc/<jmcs>/smaps` | Permission denied in all three phases | **Critical missing item:** direct `KernelPageSize`/`MMUPageSize` evidence where present | Not for negotiation itself; needed for the proposed runtime memory/veneer work |
| `/proc/<jmcs>/fd` and FD links | Permission denied in all phases | Prevents attribution of global network rows to `jmcs` | Helpful for transport diagnosis, not itself the Step 41 patch gate |
| `/proc/net` TCP/TCP6/UDP/UDP6/Unix | Available in all phases; system-wide only | Provides phase deltas, not process/socket ownership | Useful context, not a required Type111 negotiation input |
| Display/window diagnostics and bounded logcat snapshot | Available from the approved fixed commands | Contextualizes the visible stock-CarPlay state and logs | No; already captured |
| CPU/platform read-only proc/sysfs values and properties | Most selected data available; some cache/config/SELinux entries absent or undecodable | Confirms platform characteristics; does not yield page size or maps | No; already captured |

## Collection constraints for any future Lite-only observation

If fresh phase deltas later become necessary, the profile must remain limited to the ordinary fixed-operation reader in `tools/honda-readonly-preflight/collector.py`:

- Read only the existing fixed allowlist: selected `/proc`, `/sys`, properties, `/proc/net`, and bounded `dumpsys`/`logcat` operations.
- Require one expected authorized ADB target; keep command and output/time bounds.
- Write capture artifacts only on the host, outside the repository, with the existing private-directory and manifest/hash behavior.
- Do not call `PrivilegedRead`; do not construct or invoke `/system/xbin/su -c`.
- Do not use `adb root`, install/upload/execute helpers, ptrace, `process_vm_readv`, process memory, signals, stop/kill, block devices, mounts, or property/settings writes.
- Preserve permission denials as explicit unavailable results. Never translate a denial into an empty map, zero threads, or proof of absent sockets.

The existing ordinary collector already provides this profile. No new source code is needed to define it, and no enablement change to `privileged_session.py` is authorized by this document.

## What Lite does and does not close

The saved Step 40E evidence already closes the question “does every useful runtime read require root?” It does not: process/thread status, masks, global network state, platform identity, and display diagnostics were captured unprivileged.

Lite cannot close the present runtime-address question. The current process’s maps are required to calculate a valid load bias and inspect candidate gaps. `smaps` is the target’s only currently identified direct source for page-size fields in the planned capture. Older map captures belong to different PIDs/process epochs and may differ under ASLR; they cannot be substituted. ELF segment alignment, boot-image alignment, and address alignment do not prove the runtime VM page size.

## Recommendation

Treat Step 40E’s already-completed no-escalation run as the Step 40F-Lite result. Do not perform another Lite-only vehicle session now. Keep Step 40F and Step 41 blocked until an independently defensible approach obtains the specific fresh mappings/page metadata that those steps require, or the project revises Step 41 so it no longer depends on those runtime facts.
