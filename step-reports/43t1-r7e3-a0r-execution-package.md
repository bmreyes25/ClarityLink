# 43T1 R7E3 — A0-R execution package finalization

**Decision:** `R7E_A0R_EXECUTION_PACKAGE_READY`  
**Starting HEAD:** `fc2eceef2ab53c0d8ea3141f24f1571aee3802e8`  
**Implementation HEAD:** recorded after source/test/documentation commit  
**Final verification HEAD:** recorded after exact-head checks  
**Branch:** `architecture/r7e-parked-car-compatibility-preparation`  
**PR:** #19, remains open  
**Scope:** host/offline preparation only. A0-R was not executed.

## Result

R7E3 freezes the reviewed A0-R plan in [the host collector](../tools/r7e_a0r_collector.py), [machine-readable plan manifest](../research/runtime/r7e3-a0r-plan-manifest.json), [authorization packet](../research/runtime/r7e3-a0r-authorization-packet.md), and [operator runbook](../research/runtime/r7e3-a0r-runbook.md). The tool refuses by default, has a zero-ADB dry-run, requires a narrow local execution flag plus all operator inputs, pins exactly one target, uses only the reviewed reads, captures host-side evidence, redacts target identity in summaries, and never transitions automatically to A0-W or Test A.

Collector language: Python. Target command count: 11 reviewed read operations plus one local `adb devices` inventory. Mutating target commands: **NONE**. The plan manifest SHA-256 is `5b73badc219e87ef41eebb154ed4875c0c3ec2e3b19c61f2f2dc5209f3ff963e`; the collector source SHA-256 is `fcb4ce3a8acfa088bfbd706973fa7ff9f0d360dc272640fd5dea11a284ff414c`.

## ECC disposition

Target selection requires one and only one listed `device`; zero, multiple, offline, or unauthorized entries stop before target shell calls. Every target operation is pinned with `adb -s "$TARGET"`. UID other than ordinary shell 2000 stops. Release/API/ABI mismatch stops before destination reads. Exact `ls -ld` failure records destination metadata unavailable and has no fallback. `/data` `noexec` blocks; no observed `noexec` flag is not execution proof. SELinux read failure is `SELINUX_STATE_UNAVAILABLE`, with no `getenforce` fallback. All calls use a 15-second timeout and no retries. No target redirect, shell eval, wildcard, privilege escalation, target rollback command, or server manipulation exists.

`EXEC_PERMISSION_IS_TEST_A_MEASUREMENT` and `SPECIFIC_SAFE_POWER_STATE_SUFFICIENT` are preserved. A0-R remains Tier 1 `HONDA_READ_ONLY` and needs separate explicit authorization. A0-W is `BLOCKED_BY_A0_R_RESULT` and needs separate Tier 2 authorization if later evidence shows it is needed. Test A remains `BLOCKED_BY_A0` / `NOT_AUTHORIZED` and requires its own later authorization. `A0R_PASS_FOR_REVIEW` means only that evidence is ready for human review.

## Verification

- Collector fixture tests: 14 passed.
- Canonical repository suite: 893 passed, 17 skipped.
- Self-locator smoke: 3 passed.
- Simulator checks: passed (three simulator checks and Type111 failure twin).
- Repository health: to be recorded after all R7E3 reports are indexed.
- `git diff --check`: passed.
- ShellCheck: unavailable; no dependency installed for it.
- Offline CI / CodeQL: to be recorded for the exact final pushed head.

The system Python initially lacked pytest; a temporary external virtual environment was used, with the repository's pinned pytest range and required `cryptography` dependency. No project dependency or lockfile was changed.

## Decision and limits

First separately authorizable action: **A0-R ONLY**. Next: `READY_FOR_EXPLICIT_USER_A0R_AUTHORIZATION`. A0-W and Test A are not authorized. No Honda commands, writes, target discovery, vehicle interaction, file write on Honda, executable transfer, display action, USB/iAP2, MFi, real iPhone, or live CarPlay action occurred.
