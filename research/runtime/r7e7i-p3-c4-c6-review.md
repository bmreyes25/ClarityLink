# P3-C4 through P3-C6 review

## Current decision

**`TEST_A_BLOCKED_WITH_EXACT_REASON`**. Phase S has not run: no genuine, independently reviewed clock attestation exists. Current process mappings and relaunch paths therefore remain unresolved. Phase C cleanup has not occurred; the last preserved Phase R evidence says the exact file was present with expected metadata and MD5. The exact path's current absence is not established. A new Test A authorization is not proposed as ready.

No Honda, physical-device ADB, target write, `rm`, Test A, or Phase S command was run in this work. The only ADB run below used a dedicated API17 x86 emulator, a unique AVD, private ADB server, exact emulator serial, and `ADB_USB=0`.

## C4: conditional Phase C cleanup

The proposed exact command sequence and expected file identity are in [the conditional manifest](r7e7i-phase-c-cleanup-manifest.json). Fresh pre-delete identity must require one exact regular-file listing (`0555`, `shell:shell`, 7904 bytes, exact basename) and an exact MD5 match. After that, current process-safety evidence must establish no current process mapping or open executable reference and independently resolve relaunch routes, with no visibility gap or unexplained relaunch. A separate reviewer must bind those evidence identities and a newly issued, single-use authorization to the frozen source/manifest hashes.

The collector [r7e7i_phase_c_cleanup.py](../../tools/r7e7i_phase_c_cleanup.py) defaults to no ADB and prints a dry-run plan. Its live entry point deliberately rejects execution because C1 did not produce a defensible clock attestation and C3 did not establish process safety; no reviewed single-use authorization verifier or production authorization exists. The separately callable rehearsal state machine was exercised only with fake ADB. It covers exact identity and one removal, identity/hash mismatch, absent file, unexpected metadata, timeout, permission failure, and post-delete verification failure. Every fault stops without a retry; deletion appears exactly once in the fake success case.

The historical Phase R artifact contained the expected 7904-byte `0555` `shell:shell` regular file with MD5 `6137a693a77646aaf9a4cf0f351731d4`. That observation is historical only. Phase R did not inspect processes, and a pathname unlink would not terminate an open executable. Cleanup remains `PHASE_C_NO_GO`.

The current tool SHA-256 is `730c23edd95038bfe4be50e67bef9a58e36d128f92f26dd7649b05aa827c98a0`. The manifest records this identity but is not a live package authorization. Its rehearsal entry point accepts only a runner marked as fake, and its live entry point always fails closed. It must be re-frozen together with a reviewed verifier, signed process-safety evidence schema, and genuinely new one-use authorization before any future Phase C request.

## C5: API17 stress timeout

The failed preserved run `api17-runtime-cc036acc4cab.json` has SHA-256 `c168f5fe3c3e6069a38b2150d7b4c129320983a7886e4e701c2ac3a96a8e7982`. It records 51 full successful pairs, then rep 52 `--version` at 0.7554 seconds, followed by a 12-second host timeout on rep 52 `--self-test`. Captured output ends at `SELF_TEST_PASS`; it lacks `SUPERVISOR_CHILD_REAPED` and `__R7E6_STATUS:0`. The JSON has no guest-exit status, parent wait/reap timing, SIGCHLD timing, per-stage ADB latency, emulator CPU/scheduler pressure, or host subprocess timing beyond completed invocations. The cause cannot be resolved from preserved evidence. `SELF_TEST_PASS` proves only that the test routine reached its marker; it does not establish supervisor reap or guest exit.

Independent evidence confirms that the same production x86 diagnostic subsequently completed all 100 pairs: `api17-runtime-69ad6acbcd28.json`, SHA-256 `297e1dd98b93947a7e1595a7d48474c56f618f9f6ed544305ec7f8d84bf3a71c`, with maximum pair duration 1.9353 seconds and no cleanup failures. A new bounded isolated emulator rehearsal in this milestone completed five pairs: `api17-runtime-36f16acd85af.json`, SHA-256 `eaed625c471cdc3c2e34852e4200a8947522aa6f0462e08344aca390f706cb84`; max pair was 1.6476 seconds, all focused lifecycle/fault cases completed, and owned emulator/ADB cleanup had no failures. These passing runs reduce concern about a deterministic failure but do not explain or erase the original timeout. The host timeout remains 12 seconds; no watchdog limit was raised, no diagnostic lifecycle code was changed, and the old run is not reclassified as PASS.

Test A timeout risk remains material because the original timeout's terminal lifecycle markers were missing and the reproducing experiment lacks host/guest stage instrumentation that could distinguish scheduling, guest CPU pressure, ADB latency, output buffering, or subprocess behavior. Require a newly reviewed Test A timeout/rollback plan and separate authorization before any Test A.

## C6: readiness evidence

- **Phase S evidence:** insufficient. The clock attestation is absent; prior Phase S rehearsal uses synthetic fixtures only.
- **Current process/relaunch safety:** unknown. Do not infer safety from reboot, empty `ps`, or pathname absence.
- **Phase C cleanup:** not completed; no `rm` was run.
- **Exact old path absence:** not established; last private Phase R evidence found it present.
- **API17 timeout:** later 100-pair and new five-pair emulator runs pass, but the original failed run remains unexplained and its 12-second timeout risk is open.
- **Production ARMv7 artifact:** local artifact SHA-256 remains `9e20d1ad715be6c9974f9a89e1aa310283bc128f87350fb05cb224b8e247c063` (7,904 bytes). No production artifact was rebuilt or modified.
- **Collector:** the existing Test A collector and Phase S collector were not changed. C4's new rehearsal collector is default-disabled and cannot execute live until a separately reviewed package verifier and authorization are implemented.

### Exact stop reasons

1. `PHASE_S_BLOCKED`: missing real, independent signed clock attestation and current host clock bounds.
2. `CURRENT_PROCESS_SAFETY_UNKNOWN`: no adequate current mapping/open-reference/relaunch evidence.
3. `PHASE_C_NOT_COMPLETED`: this milestone forbids Honda operations and deletion.
4. `EXACT_TARGET_PATH_ABSENCE_UNPROVEN`: preserved Phase R observed the exact file present; no later absence evidence exists.
5. `API17_TIMEOUT_ROOT_CAUSE_UNDETERMINED`: failed run omits telemetry required to isolate the cause; timeout risk remains.

Decision: **`TEST_A_BLOCKED_WITH_EXACT_REASON`**. No authorization carries forward. A future authorization requires new, current evidence and a separate explicit decision.

## ECC review and verification

ECC security review and Python testing guidance were applied to exact-path scope, default-disabled operation, one-shot state progression, timeout/permission stops, and fault-injection tests. Focused C1-C4/C6 regression set: 218 passed. Dry-run: `DRY_RUN_NO_ADB`, zero ADB operations. Python syntax compilation and `git diff --check` passed. API17 x86 focused emulator rehearsal: 5/5 version/self-test pairs plus existing fault matrix; private evidence is referenced above. The host timeout-instrumentation fault regression also passed. No Phase S, Honda, physical-device ADB, target write, cleanup, or Test A execution occurred.
