# Step 40E — Honda read-only runtime capture

## Result

**Step 40E capture: COMPLETE, with explicit evidence limits.** The initial `exec-out`/`uname` failure did not establish that ADB was broken. The user supplied successful manual `adb shell` reads and identified that `uname` is absent on this embedded Android build. The collector was corrected to use the legacy `adb shell` service, classify missing utilities separately, and fingerprint from `/proc/version` plus exact Android properties. The corrected collector matched the target and completed baseline, stock CarPlay connected, and post-disconnect phases.

The raw capture is host-only at `~/CLARITY_RUNTIME_20260929_195051`; offline analysis is next to it at `~/CLARITY_RUNTIME_20260929_195051_analysis.json`. Neither is in the Git worktree. The manifest lists 1,943 artifacts; all 1,944 host SHA-256 entries (artifacts plus manifest) verified with zero mismatches. An earlier capture bundle was retained outside Git but not used for conclusions because API-17 toolbox `ls` rejected `-1`; the corrected capture uses plain `ls`.

## Manual preflight facts — separate from automated capture

The following are user-supplied results from manual, read-only commands. They are recorded as separate preflight evidence and are not represented as bytes from the automated bundle:

- Kernel `3.1.10+`, `SMP PREEMPT`, built Thu Apr 5 02:19:35 JST 2018
- Compiler gcc 4.6.x-google 20120106 prerelease
- ARMv7, four logical CPUs; implementer `0x41`, CPU part `0xc09`, revision 9
- Hardware `vcm30t30`, device `vcm30t30a`, board `Andromeda`
- Android 4.2.2 / API 17
- ADB shell UID 2000 (`shell`) with reported graphics, input, log, adb, and networking groups

The corrected automated preflight independently matched `/proc/version` and the Android release, SDK, device, board, and hardware properties. The target identity is a **MATCH**.

## Phase observations

| Area | Baseline: phone disconnected | Stock CarPlay connected | Post-disconnect |
|---|---|---|---|
| `jmcs` process | Identified | Same process identity | Same process identity |
| Threads | 14 observed; five snapshots consistent | 29 accessible; one short-lived TID per snapshot vanished before status read; partial | 14 observed; five snapshots consistent |
| Process signal masks | Complete | Complete | Complete |
| Per-thread signal masks | Complete for observed set | Partial due to transient TID | Complete for observed set |
| `wchan` | Available for observed set | Partial | Available for observed set |
| `/proc/<jmcs>/maps` and `smaps` | Permission denied | Permission denied | Permission denied |
| `/proc/<jmcs>/fd` listing | Permission denied | Permission denied | Permission denied |
| Global TCP4/TCP6/UDP4/UDP6 rows | 6 / 3 / 4 / 2 | 6 / 6 / 7 / 5 | 6 / 5 / 4 / 2 |
| CPU topology | CPU0–CPU3 topology fields read | Not recaptured in delta phase | Not recaptured in delta phase |

The process PID and start-time identity remained unchanged across all phases. Network rows are system-wide `/proc/net` observations; FD access was denied, so sockets cannot be attributed to `jmcs`. The user-confirmed Apple Maps snapshot was collected during the connected phase.

## Unavailable evidence and limits

- **Page size, load bias, INFO/Setup runtime callsites, mapping permissions, and veneer gaps:** unknown. The shell UID 2000 could not read root-owned `jmcs` maps/smaps. Do not interpret empty analysis arrays as an empty address space.
- **Stable common veneer gap:** unknown; no live mapping data exists to calculate one.
- **Cache line/topology details:** CPU0–CPU3 topology values were read in baseline; cache index and coherency-line values were not exposed by the available listing. The manual four-core observation is separately attributed above.
- **Kernel config:** `/proc/config.gz` was returned but did not decompress as supported gzip, so selected config values remain unavailable.
- **SELinux enforcement:** `/sys/fs/selinux/enforce` was not present. ASLR read-only value was `2` in baseline.
- **Executable symlink:** toolbox did not expose `/proc/<jmcs>/exe` through `ls -l`; identity was corroborated by `/proc/<pid>/status` Name, NUL-delimited cmdline, PID, and stat start time. `uname` was correctly classified COMMAND_UNAVAILABLE; no transport failure was inferred.

No `adb root`, privilege escalation, target setting changes, signals, suspension, ptrace, `/proc/PID/mem`, helper upload/execution, target writes, `jmcs` modifications, or Type111 activity occurred. This completes the authorized read-only capture only; it does not authorize active testing.

## ECC and verification

ECC evidence-first and security-review guidance was applied to command classification, identity checks, fixed allowlist, shell argument construction, time/output limits, host-only writes, privacy handling, and the target write boundary. An independent ECC reviewer capability was unavailable; no independent approval is claimed.

| Check | Result |
|---|---|
| Focused collector/parser/analyzer tests | 35 passed |
| Honda suite | 90 passed, 1 skipped |
| Interposer suite | 14 passed |
| Transport + negotiation | 47 passed, 31 subtests passed |
| Renderer suite | 8 passed |
| Collector dry-run | Passed; no target query |
| `git diff --check` | Passed |
| Capture SHA-256 table | 1,944 file entries verified; 0 mismatches |

## Decision gate

ADB TRANSPORT: WORKING

ADB SHELL: WORKING

UNAME: UNAVAILABLE

PRIMARY IDENTITY SOURCE: /proc/version + Android properties

TARGET IDENTITY: MATCH

HONDA LIVE KERNEL: 3.1.10+, SMP PREEMPT, built Thu Apr 5 02:19:35 JST 2018; gcc 4.6.x-google 20120106 prerelease

HONDA LIVE ANDROID: 4.2.2

HONDA LIVE SDK: 17

HONDA LIVE DEVICE: vcm30t30a

HONDA LIVE BOARD: Andromeda

HONDA LIVE HARDWARE: vcm30t30

HONDA LIVE CPU: ARMv7; 4 logical CPUs; implementer 0x41; part 0xc09; revision 9

JMCS IDENTIFIED: YES

JMCS LOAD BIAS: UNKNOWN — maps denied

TARGET PAGE SIZE: UNKNOWN

SMAPS: PERMISSION DENIED

THREAD DATA: PARTIAL — baseline/post stable; connected snapshot had transient TIDs

SIGNAL MASK DATA: PARTIAL — process masks complete; connected per-thread set partial

WCHAN: PARTIAL — baseline/post available; connected partial

COMMON VENEER GAP: UNKNOWN

COMMON GAP STABLE ACROSS PHASES: UNKNOWN

JMCS SAME PROCESS ACROSS CARPLAY: YES

TARGET WRITES: 0

CUSTOM CODE EXECUTED: 0

JMCS MODIFIED: NO

TYPE111 ACTIVITY: NONE

ECC WORKFLOW: USED

ECC INDEPENDENT REVIEWER: UNAVAILABLE

STEP 40E: COMPLETE

READY FOR STEP 40F: NO

READY FOR STEP 41: NO

READY FOR TYPE111: NO

BIGGEST BLOCKER: Unprivileged ADB shell cannot read `/proc/<jmcs>/maps` or `smaps`, preventing runtime addresses, page size, and veneer-space evidence.
