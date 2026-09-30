# Step 40E2 — Offline capture review and privileged-read preparation

**Status: OFFLINE ANALYSIS COMPLETE; vehicle session NOT READY.** No ADB/device command was run during Step 40E2. The car can remain off. No live collection, Step 40F, helper execution, ptrace, signals, or `jmcs` modification occurred.

## Existing Step 40E bundle

The immutable bundle at `~/CLARITY_RUNTIME_20260929_195051` was not modified. Its manifest lists 1,943 artifacts; the 1,944 SHA-256 records cover those artifacts plus `manifest.json`. All 1,944 matched. The sanitized, machine-readable inventory and detailed private derivatives were written beside the raw bundle:

- `~/CLARITY_RUNTIME_20260929_195051_derived_inventory.json` — 1,944 rows with normalized paths, phase, operation, status, size, SHA-256, and purpose.
- `~/CLARITY_RUNTIME_20260929_195051_derived_threads.json` — per-TID/per-phase observations, snapshot coverage, and signal-mask analysis. This remains outside Git because it contains TIDs and status metadata.
- `~/CLARITY_RUNTIME_20260929_195051_derived_network.json` — decoded TCP/UDP/Unix rows and deltas. It remains outside Git because it contains endpoints, ports, and inodes.

Inventory outcomes: 1,807 available, 98 empty/not exposed, 26 other command failures, 11 permission denied, and 2 command unavailable. Those outcomes include historical attempts, not just the three map reads.

### Threads and signals

| Phase | Listed each snapshot | Status readable each snapshot | Snapshot result |
|---|---:|---:|---|
| Baseline | 14 | 14 | Same set in all five |
| Stock CarPlay connected | 30 | 29 | Same 29 readable TIDs in all five; one distinct TID disappeared before each status read |
| Post-disconnect | 14 | 14 | Same set in all five |

Across phases the observations include 13 TIDs present in all phases, one baseline-only TID, one TID appearing during connected and remaining post-disconnect, 15 additional connected-only readable TIDs, and five distinct connected-only TIDs with no status due to the race. The 14 → 29 → 14 change is repeatable within the five snapshots in this one session; it was not repeated across separate CarPlay sessions. TID names and states are in the private derivative; no thread role is inferred here.

All readable per-thread masks were decoded using Linux ARM numbering. The connected phase is incomplete for its five missing status records. Across available records, `SIGABRT`, `SIGHUP`, `SIGINT`, `SIGQUIT`, and `SIGTERM` appeared in some blocked masks; `SIGPIPE` appeared ignored; pending masks were empty. The process masks were stable across phases: no pending signals, `SIGPIPE` ignored, and `SIGILL`, `SIGABRT`, `SIGBUS`, `SIGFPE`, `SIGSEGV`, and signal 16 caught. No “safe” signal or rendezvous candidate is declared.

### Network and security state

Global TCP4/TCP6/UDP4/UDP6 row counts were 6/3/4/2 at baseline, 6/6/7/5 connected, and 6/5/4/2 post-disconnect. Decoded endpoint deltas show four new TCP6, four new UDP4, and four new UDP6 rows present only during the connected snapshot, plus one departing TCP6, one departing UDP4, and one departing UDP6 row. No newly observed endpoint remained after disconnect under the local/inode comparison. `/proc/net` is system-wide; inaccessible `jmcs` FDs mean none of these sockets is attributed to `jmcs`.

`jmcs` status records show UID/GID 0 and `TracerPid: 0`; no `Dumpable` value was present. The captured `/proc` mount options contain no `hidepid` option. ASLR was `2`. `/sys/fs/selinux/enforce` was absent; this does not prove there are no vendor LSM checks. Cache index directories were unavailable. The existing `proc/config.gz` bytes start with the gzip signature, but the legacy shell copy did not decompress. No direct page-size value exists in the capture. **Target page size: UNKNOWN.**

## Procfs denial analysis

The actual live errors are `Permission denied` for root-owned `jmcs` `maps`, `smaps`, and `fd` under shell UID 2000. Closely related Android Tegra source shows ptrace-eligibility checks protecting process maps and FD visibility. That makes UID/ptrace gating **high confidence**, but not exact Honda-kernel confirmation: the Honda 3.1.10+ source/config, `Dumpable`, capability state of the caller, and vendor LSM decision are not all available. See [proc access research](../research/platform/honda-proc-access.md).

## Existing privileged path and blocker

The immutable local system-vendor archive contains `/system/xbin/su`, an ARM EABI5 Chainfire SuperSU-family binary. Static strings document `su -c COMMAND`; earlier read-only sessions show successful `su -c id` with UID 0. No `adb root` is planned. Using an already-installed facility needs no install, chmod, service enablement, or config edit. Whether SuperSU invocations can create daemon/log state is unknown.

The archived file metadata is **root:root, mode 06777 (`-rwsrwsrwx`)**, unsafe because group and other can write a setuid-root executable. The code therefore verifies the target binary’s SHA-256, owner, setuid bit, and non-writable group/other mode through ordinary unprivileged reads before invoking `/system/xbin/su`. The known archive mode fails this guard. The current live hash/mode have not been checked and must not be assumed. This is the controlling safety finding; the session simulator passes, but the collector intentionally will refuse to proceed if this mode is still present.

## Prepared host tooling

`tools/honda-readonly-preflight/privileged.py` provides `PrivilegedRead` with enum-only operations. It has no public arbitrary-root-command API. PIDs/TIDs/FDs are positive decimal integers; file leaves and network tables are fixed; user strings never become a shell program. The command uses the exact `/system/xbin/su -c <fixed command>` form. The reader verifies UID 0 before process/FD/thread/network groups and checks stable `jmcs` PID/start-time identity across phases.

`privileged_session.py` is one host invocation for the baseline / stock-CarPlay / post-disconnect three-phase sequence. It reads only identity/status/maps/smaps/limits/mountinfo/scheduler/oom/cgroup metadata, bounded thread status/stat/wchan snapshots, FD symlink metadata, global socket tables, and optional base64-encoded `/proc/config.gz`. It never reads `/proc/PID/mem`, `/proc/PID/environ`, pagemap, or auxv; it uploads/runs no helper and sends no signals. Raw results are written under a new mode-0700 host directory outside Git, with mode-0600 artifacts, a manifest, and a final SHA-256 table. If required maps access fails, it stops before prompting for stock CarPlay.

Terminal success is emitted only after finalization:

```text
==============================================
CAPTURE COMPLETE — YOU CAN TURN THE CAR OFF NOW
==============================================
```

Safe aborts use the corresponding `CAPTURE STOPPED — YOU CAN TURN THE CAR OFF NOW` message. Output-limit, timeout, missing-command, PID-change, maps denial, and finalization failure paths are covered by offline session tests. No command was sent to Honda while testing.

The live CLI is mechanically disabled (`LIVE_CAPTURE_ENABLED = False`) until the archived `su` integrity/mode blocker is resolved and reviewed. The dry-run path remains available without ADB device commands.

## ECC and verification

ECC `security-review` and `terminal-ops` workflows were applied to the trust boundary, shell construction, path/identifier validation, read allowlist, target writes, output bounds, privacy, and stop/finalization behavior. No independent ECC reviewer capability is available in this session; this is not an independent approval.

Focused collector/analyzer/security tests: 54 passed. Honda suite: 109 passed, 1 skipped. Interposer: 14 passed. Transport/negotiation: 47 passed, 31 subtests passed. Renderer: 8 passed. Integration: 1 passed. Pytest was installed into a temporary host-only target directory; no repository dependency was added. Python syntax compilation, the fixed-command dry-run, and `git diff --check` pass. No ADB device command was run.

**Expected machine collection time: NOT MEASURED.** The vehicle session is blocked at the preflight integrity decision, and host fixture timing would not reliably predict legacy-device procfs and ADB latency. Human CarPlay transition time is also excluded and unknown.

## Decision

The preparation code and complete phase simulator are ready for review, but **the vehicle session is NOT READY** because the preserved setuid binary has mode 06777, the live file fingerprint is unknown, and independent ECC review is unavailable. The CLI now refuses live execution before initializing ADB. No single command is provided for a vehicle visit. Resolve the binary integrity/mode finding offline and obtain reviewer coverage before reconsidering a live session.

Step 40F: **NO**. Step 41: **NO**. Type111: **DISABLED**.
