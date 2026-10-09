# R7E Test A — temporary executable acceptance plan

**Plan state:** `BLOCKED_BY_A0` / `NOT_AUTHORIZED` (artifact closed; A0-R required first).
**Risk:** Tier 2 (temporary project process/file).  
**Question:** Can the project-owned API17/ARMv7 diagnostic start and terminate cleanly on the Honda platform, without display, USB/iAP2, or CarPlay behavior?

## Blockers and prerequisites

1. **Closed offline:** build/audit split artifact; Test A CLI SHA-256 `f2e12aafe221ff51e153ccc7c1b71402cf3cf0c3a4f1648fb5963e2e66cffca0`; ELF32 ARM EABI5/API17; 10 imports, zero unknown; dependencies `libdl.so` and `libc.so`.
2. **Closed offline:** no-argument, help/version/status/self-test, invalid-mode, bounded-resource, and 100-cycle checks passed; see R7E1 offline test report.
3. A0-R establishes current candidate destination metadata, mount flags, visible SELinux observation, and operator-observed power mode; A0-R is separately authorized and read-only.
4. If write/delete remain unknown, separately authorize A0-W; it must not execute any program. Do not require pre-proof of successful executable mapping: this is Test A's measurement (`EXEC_PERMISSION_IS_TEST_A_MEASUREMENT`), subject to A0-R showing no known mount/policy blocker.
5. Separately reviewed exact Test A commands, rollback, and Test A authorization remain mandatory.

## Proposed later actions (NOT EXECUTED)

**PROPOSED — NOT EXECUTED.** Exact sequence remains blocked until destination and shell-command/rollback capabilities are established. Artifact is exactly `claritylink-target-diag`, SHA-256 `f2e12aafe221ff51e153ccc7c1b71402cf3cf0c3a4f1648fb5963e2e66cffca0`. Use `DESTINATION_FROM_APPROVED_A0_RESULT` as a documentation gate only; it is not a runnable command. Do not guess a destination. Verify local canonical SHA-256, optional MD5, and mode 0755 before transfer. ADB push the exact artifact, then verify remote mode with `ls -l`; if executable permission is absent, STOP and do not run target `chmod`. If A0-R established `/system/bin/md5`, compare target MD5 as transport consistency only. SHA-256 remains canonical identity. Then run `--version`, then `--self-test`, record status/output, verify normal process exit, remove only the exact artifact with proven `rm`, verify exact absence, and observe normal UI/cluster/warnings/audio. Unexpected process persistence stops normal flow; only a separately reviewed exact PID discovery and exact PID `kill` may be considered. No display, Presentation, frame, listener, USB/iAP2, MFi, or CarPlay operation.

## Write and privilege audit

| Action | Reads | Writes/files | Processes/resources | Privilege |
|---|---|---|---|---|
| Transfer exact artifact (future) | Target destination metadata | One temporary file, exact size/hash/mode to be recorded | No persistent process | Ordinary shell preferred; actual need unknown |
| Run self-test (future) | Runtime/API inventory only | No persistent data; bounded transient resources only | One foreground process; no listeners or display | Ordinary shell preferred; unknown until validated |
| Cleanup (future) | File metadata and process/resource status | Remove only exact temporary artifact | Terminate only the named project process | Exact mechanism requires evidence |

No system partition, package manager, startup/init, `jmcs`, `/dev/i2c-2`, CAN, USB, or display state changes are allowed. Test A classification is `HOST_ONLY` for current preparation; eventual target execution includes `HONDA_TEMPORARY_WRITE` if transfer is required.

## Vehicle, stop, rollback, and result

Future test state must be separately approved and directly observed: stationary, parked, exact named power mode, center display fully booted, cluster normal/no warnings, and operator able to terminate. A theoretical minimum mode is unnecessary (`SPECIFIC_SAFE_POWER_STATE_SUFFICIENT`). `ps`/`kill` and `rm` are not yet proven; no wildcard stop/removal. Do not call rollback ready until exact process-disposition and removal commands are evidence-backed. Reboot is not assumed rollback.

Success/failure would establish only `HONDA_PROTOTYPE_OBSERVED` execution behavior under recorded conditions. Failure means stop and preserve sanitized logs; it does not imply a broader compatibility verdict. No test is run now. **Readiness: `BLOCKED_BY_A0`** because live destination/state observations and exact command/rollback evidence are unestablished.

## R7E4 research-backed refinement (offline only)

The prior manifest SHA-256 `5b73badc219e87ef41eebb154ed4875c0c3ec2e3b19c61f2f2dc5209f3ff963e` is `SUPERSEDED_BEFORE_AUTHORIZATION`; no authorization was granted under it. The normalized manifest at [r7e3-a0r-plan-manifest.json](r7e3-a0r-plan-manifest.json) now carries plan version `R7E4-A0R-COMMAND-SET-1` and SHA-256 `962b25fca36dabde11f2406da1e5d898a0fe5c3a49f78f2bd00f292910442004`. Its six added A0-R commands are fixed `ls -l` metadata reads for `/system/bin/toolbox`, `rm`, `ps`, `kill`, `md5`, and `chmod`; none executes those tools. Missing tool entries are recorded as `<TOOL>_UNAVAILABLE` and remain informational for A0-R; missing `rm`, `ps`, or `kill` also records a separate future-plan review blocker, while missing optional `md5` or unnecessary-by-default `chmod` does not block A0-R. `SELINUX_STATE_UNAVAILABLE` is informational and is never interpreted as disabled or permissive. `/data` `noexec` remains a hard blocker.

For future Test A, require host artifact mode `0755` before transfer, then verify the remote mode with `ls -l`; if the target executable bit is absent, stop without automatic `chmod`. SHA-256 remains the canonical identity; MD5 is optional transport consistency only. A0-W is proposed as one unique inert `0644` marker pushed through ADB sync, read-only inspected and optionally MD5-compared, then removed by exact path with a proven `rm`; it remains separately unauthorized and must not auto-run. See [R7E4 Android 4.2.2 research](r7e4-android42-target-path-research.md).
