# R7E3 A0-R authorization packet

**Purpose:** collect current identity, platform, destination metadata, mount flags, visible SELinux state, and operator-observed vehicle state for human review. **Risk:** Tier 1 `HONDA_READ_ONLY`. **Current status:** prepared only; not authorized and not executed.

## Frozen implementation

- Repository/branch: `bmreyes25/ClarityLink`, `architecture/r7e-parked-car-compatibility-preparation`.
- Collector: `tools/r7e_a0r_collector.py`.
- Collector source SHA-256: `fcb4ce3a8acfa088bfbd706973fa7ff9f0d360dc272640fd5dea11a284ff414c`.
- Plan manifest: [r7e3-a0r-plan-manifest.json](r7e3-a0r-plan-manifest.json).
- Plan manifest SHA-256: `962b25fca36dabde11f2406da1e5d898a0fe5c3a49f78f2bd00f292910442004`.
- Exact collector commit: `47605adad4e83faa8e05e028cd46282848546139`; a source or manifest change invalidates prior authorization.
- Command count: 17 target reads, plus one host-only inventory; target writes **ZERO**.

## Exact commands

1. `A0R-00` `adb devices`
2. `A0R-01` `adb -s "$TARGET" shell id`
3. `A0R-02` `adb -s "$TARGET" shell getprop ro.build.version.release`
4. `A0R-03` `adb -s "$TARGET" shell getprop ro.build.version.sdk`
5. `A0R-04` `adb -s "$TARGET" shell getprop ro.product.cpu.abi`
6. `A0R-05` `adb -s "$TARGET" shell pwd`
7. `A0R-06` `adb -s "$TARGET" shell ls -ld /data`
8. `A0R-07` `adb -s "$TARGET" shell ls -ld /data/local`
9. `A0R-08` `adb -s "$TARGET" shell ls -ld /data/local/tmp`
10. `A0R-09` `adb -s "$TARGET" shell cat /proc/mounts`
11. `A0R-10` `adb -s "$TARGET" shell cat /proc/self/status`
12. `A0R-11` `adb -s "$TARGET" shell cat /sys/fs/selinux/enforce`
13. `A0R-12` `adb -s "$TARGET" shell ls -l /system/bin/toolbox`
14. `A0R-13` `adb -s "$TARGET" shell ls -l /system/bin/rm`
15. `A0R-14` `adb -s "$TARGET" shell ls -l /system/bin/ps`
16. `A0R-15` `adb -s "$TARGET" shell ls -l /system/bin/kill`
17. `A0R-16` `adb -s "$TARGET" shell ls -l /system/bin/md5`
18. `A0R-17` `adb -s "$TARGET" shell ls -l /system/bin/chmod`

Each ADB operation is bounded to 15 seconds. The complete operation audit and stop semantics are in the [command manifest](r7e3-a0r-command-manifest.md).

## Required operator conditions

Before collection, the operator must separately authorize this exact A0-R package and supply a local authorization reference. The operator must directly observe and record the exact power-state label (unknown text is allowed as text; it is never inferred or normalized), confirm the vehicle is stationary and parked, center display fully booted, cluster normal, and no unexpected warnings, record the relevant audio state or `NOT_RELEVANT`, and confirm the sole listed ADB target is the intended Honda. Afterward the operator records exact UI/cluster/warning/audio observations; only `STOCK_STATE_UNCHANGED` permits a non-stop result. If any required confirmation is absent, stop.

The collector accepts only exactly one listed target in `device` state. Zero, multiple, offline, unauthorized, or malformed inventory stops without a shell command. The selected identity is pinned for every target operation. No topology is inferred. No scan, retry, reconnect, or generic fallback is allowed.

## Stop conditions and evidence

Stop on ambiguous target, non-UID-2000 shell, platform mismatch from Android 4.2.2/API17/ARMv7-compatible ABI, any required command failure, timeout, missing `/data` mount row, `/data` `noexec`, failed exact `ls -ld` metadata, vehicle/UI anomaly, or any plan divergence. SELinux file absence/denial/unreadability/invalid data is recorded as informational `SELINUX_STATE_UNAVAILABLE`, never disabled or permissive, and never triggers `getenforce`.

Local evidence includes metadata, run ID, collector/plan versions, repository HEAD, local authorization reference, exact observed power-state text, confirmations, command IDs and operations, monotonic and UTC timestamps, exit statuses, classifications, stdout/stderr, full `/proc/mounts`, parsed `/data` filesystem/options/`rw`/`ro`/`noexec`/`nosuid`/`nodev`, and redacted target identity. Raw selector is confined to the private ignored local evidence package. No VIN is requested or stored. Target rollback commands: **NONE**; an unexpected mutation is a STOP/INCIDENT.

## What success means

`A0R_PASS_FOR_REVIEW` means only that the fixed read-only observations were collected for review. `NO_NOEXEC_FLAG_OBSERVED` does not demonstrate successful execution. `EXEC_PERMISSION_IS_TEST_A_MEASUREMENT` remains preserved. Favorable destination metadata does not prove write/delete; if it remains unproven, the result may state `WRITE_DELETE_EVIDENCE_STILL_REQUIRED` for a later separate A0-W review.

**A0-W NOT AUTHORIZED. TEST A NOT AUTHORIZED.** This package has no automatic continuation into either stage. A0-W remains `BLOCKED_BY_A0_R_RESULT`; Test A remains `BLOCKED_BY_A0` / `NOT_AUTHORIZED` until a human reviews actual A0-R evidence and separately decides.

## Old manifest `5b73badc219e87ef41eebb154ed4875c0c3ec2e3b19c61f2f2dc5209f3ff963e` is `SUPERSEDED_BEFORE_AUTHORIZATION`; no authorization was granted under it.

Sample authorization text — NOT GRANTED

> I authorize ClarityLink A0-R only, using collector commit `47605adad4e83faa8e05e028cd46282848546139` and plan manifest SHA-256 `962b25fca36dabde11f2406da1e5d898a0fe5c3a49f78f2bd00f292910442004`, against my parked 2018 Honda Clarity under the stated operator gates. I do not authorize A0-W, Test A, file writes, executable transfer, display activity, USB/iAP2, MFi, or CarPlay.

This is sample wording for later review; the user has not granted this authorization. The runtime `--execute-authorized-a0-readonly` option is only a conscious local mode gate and does not grant authorization.

## R7E4 research-backed refinement (offline only)

Prior manifest SHA-256 `5b73badc219e87ef41eebb154ed4875c0c3ec2e3b19c61f2f2dc5209f3ff963e` is `SUPERSEDED_BEFORE_AUTHORIZATION`; no authorization was granted under it. The normalized manifest at [r7e3-a0r-plan-manifest.json](r7e3-a0r-plan-manifest.json) now carries plan version `R7E4-A0R-COMMAND-SET-1` and SHA-256 `962b25fca36dabde11f2406da1e5d898a0fe5c3a49f78f2bd00f292910442004`. Its six added A0-R commands are fixed `ls -l` metadata reads for `/system/bin/toolbox`, `rm`, `ps`, `kill`, `md5`, and `chmod`; none executes those tools. Missing tool entries are recorded as `<TOOL>_UNAVAILABLE` and remain informational for A0-R; missing `rm`, `ps`, or `kill` also records a separate future-plan review blocker, while missing optional `md5` or unnecessary-by-default `chmod` does not block A0-R. `SELINUX_STATE_UNAVAILABLE` is informational and is never interpreted as disabled or permissive. `/data` `noexec` remains a hard blocker.

For future Test A, require host artifact mode `0755` before transfer, then verify the remote mode with `ls -l`; if the target executable bit is absent, stop without automatic `chmod`. SHA-256 remains the canonical identity; MD5 is optional transport consistency only. A0-W is proposed as one unique inert `0644` marker pushed through ADB sync, read-only inspected and optionally MD5-compared, then removed by exact path with a proven `rm`; it remains separately unauthorized and must not auto-run. See [R7E4 Android 4.2.2 research](r7e4-android42-target-path-research.md).
