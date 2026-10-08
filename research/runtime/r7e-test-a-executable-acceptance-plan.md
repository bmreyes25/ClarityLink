# R7E Test A — temporary executable acceptance plan

**Plan state:** `BLOCKED_BY_EVIDENCE` / `NOT_AUTHORIZED`  
**Risk:** Tier 2 (temporary project process/file).  
**Question:** Can the project-owned API17/ARMv7 diagnostic start and terminate cleanly on the Honda platform, without display, USB/iAP2, or CarPlay behavior?

## Blockers and prerequisites

1. Build the R7E-specific fail-closed diagnostic offline and record its exact SHA-256, ELF32 ARM EABI5 ABI, API17 imports, dependencies, and manifest. It does not currently exist.
2. Complete its no-argument, self-test, invalid-mode, bounded-resource, and shutdown tests offline.
3. Establish an exact temporary destination and prove its write/delete semantics. `/data/local/tmp` is only a candidate and remains `EVIDENCE_REQUIRED`.
4. Establish minimum head-unit power state from evidence. Current evidence does not distinguish accessory/ON/READY: `VEHICLE_POWER_STATE_REQUIRES_CONFIRMATION`.
5. Have a separately reviewed, exact Test A plan and explicit Test A authorization.

## Proposed later actions (NOT EXECUTED)

No exact transfer/invocation command can be responsibly specified until artifact hash, destination, executable format, and target shell/runtime acceptance are known. Do not substitute guessed values or run a package install. Once those values are established offline, this section must be revised to list literal commands and each command's write audit before review. There is no display, Presentation, Surface, frame, listener, USB/iAP2, MFi, or CarPlay operation in Test A.

## Write and privilege audit

| Action | Reads | Writes/files | Processes/resources | Privilege |
|---|---|---|---|---|
| Transfer exact artifact (future) | Target destination metadata | One temporary file, exact size/hash/mode to be recorded | No persistent process | Ordinary shell preferred; actual need unknown |
| Run self-test (future) | Runtime/API inventory only | No persistent data; bounded transient resources only | One foreground process; no listeners or display | Ordinary shell preferred; unknown until validated |
| Cleanup (future) | File metadata and process/resource status | Remove only exact temporary artifact | Terminate only the named project process | Exact mechanism requires evidence |

No system partition, package manager, startup/init, `jmcs`, `/dev/i2c-2`, CAN, USB, or display state changes are allowed. Test A classification is `HOST_ONLY` for current preparation; eventual target execution includes `HONDA_TEMPORARY_WRITE` if transfer is required.

## Vehicle, stop, rollback, and result

Eventual execution must be stationary, parked, controlled, and monitored. Do not guess power state. Stop on any global stop condition, unexpected privilege, mutation, persistence, instability, or cleanup failure. Rollback: terminate the identified diagnostic process; verify it exited; remove the exact artifact; verify file absence and zero owned resources; observe normal center UI, cluster, warnings, and audio. Reboot is not an assumed rollback.

Success would establish only `HONDA_PROTOTYPE_OBSERVED` temporary execution under recorded conditions. Failure means stop and preserve sanitized logs; it does not imply a compatibility verdict. No test is run now. **Readiness: `BLOCKED_BY_EVIDENCE`** because artifact, destination, power state, and exact command are unestablished.
