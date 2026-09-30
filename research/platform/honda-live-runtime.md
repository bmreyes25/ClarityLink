# Honda live runtime evidence — Step 40E

## Provenance

The user supplied a separate manual read-only preflight: Android 4.2.2/API 17; Linux 3.1.10+ with SMP/PREEMPT; ARMv7 with four CPUs, Cortex-A9 family part `0xc09`; VCM30T30 hardware, `vcm30t30a` device, Andromeda board; ADB shell UID 2000. The reported compiler/build date are in the [Step 40E report](../../step-reports/40e-readonly-runtime-preflight.md). These manual facts are not files in the automated capture.

The corrected collector uses legacy `adb shell`, treats `uname` as optional, and verifies `/proc/version` plus exact Android release/SDK/device/board/hardware properties. All required identity values matched. The initial `exec-out`/`uname` attempt was a collector compatibility issue, not proof of a broken ADB transport.

## Automated three-phase capture

The parked capture completed baseline, normal stock CarPlay connected (including the user-confirmed Apple Maps snapshot), and post-disconnect phases. Raw capture and sibling offline analysis remain outside Git at `~/CLARITY_RUNTIME_20260929_195051` and `~/CLARITY_RUNTIME_20260929_195051_analysis.json`. The bundle hash table verified with zero mismatches.

The same `jmcs` process PID/start-time identity persisted across all phases. Baseline and post-disconnect each exposed 14 threads consistently across five snapshots. During connected CarPlay, 29 threads were readable; one transient TID per snapshot disappeared before its status read, so connected per-thread signal and wchan evidence is partial. Process signal masks were readable in all phases.

## Permission and capability limits

ADB shell runs as UID 2000 while `jmcs` is root-owned. Reads of `/proc/<jmcs>/maps`, `smaps`, and `fd` listing returned permission denied in each phase. Therefore load bias, page size, runtime callsite addresses, and veneer gaps remain unknown; empty parsed mappings must not be read as an empty process map. Global network tables were collected, but inaccessible FDs prevent attributing sockets to `jmcs`.

CPU0–CPU3 topology fields were read during baseline. Cache index/line fields were not exposed. `/proc/config.gz` did not parse as supported gzip; `/sys/fs/selinux/enforce` was absent. `uname` was classified COMMAND_UNAVAILABLE, not as a transport failure. No privilege escalation, target writes, signals, helper execution, ptrace, or Type111 activity occurred.

Step 40E is complete as a read-only capture with partial evidence. Step 40F, Step 41, and Type111 remain disabled pending the maps/smaps blocker and separate safety review.
