# 43T1 R7E6A — Final Test A collector safety closure

**Scope:** offline collector correction and new frozen authorization package. No Honda command, Honda write, physical Android contact, Test A execution, or Test A authorization occurred.

## Result

Decision: `R7E_TEST_A_EXECUTION_PACKAGE_READY`.

Next: `READY_FOR_EXPLICIT_TEST_A_AUTHORIZATION`. Test A remains `NOT_AUTHORIZED` and `NOT_EXECUTED`; Test B is separately unauthorized and cannot auto-start.

The original CodeQL concern was resolved before this milestone. On starting HEAD `fad39c42fc58638afd5d003deee3e4d97df89c58`, Offline CI, the CodeQL workflow, all configured CodeQL language jobs, and Advanced Security no-new-alerts check were verified successful. No workflow change or emulator rerun was needed to address CodeQL. The R7E6A commit still requires exact-head hosted checks.

## Collector corrections

The old absence query used `test ! -e` and treated empty output as absence. In an isolated Android 4.2.2/API17/x86 emulator, a missing-path `test -e` returned host status 0 with empty output. The revised pre-transfer and final-cleanup checks use one exact-path `ls -ld` query and accept only a strict, recognized ENOENT line naming the frozen path. Empty, mixed, multiple, permission, command-not-found, and unknown output is rejected. Existing regular files, symlinks, and directories fail the pre-transfer gate. The API17 probe created each type, confirmed its metadata, removed it exactly, and verified final absence; 59 transport-ownership checks passed and cleanup failures were zero. Raw emulator evidence remains ignored under `build/`.

The MD5 parser now requires exactly one 32-hex digest, one separating space, and the exact frozen remote path. It rejects wrong paths, duplicate lines, truncated data, and extra output.

Failure cleanup is conditioned on process state. After a diagnostic invocation begins, cleanup is allowed only when the exact supervisor start/reap records match and both reported PIDs are confirmed absent. A timeout or uncertain lifecycle/process state causes the collector to stop without removing the executable and preserves a redacted private failure record. A known-exited failure permits only the exact-path removal and strict absence check. No external `ps`, `kill`, wildcard, retry, or fallback is used.

## Frozen package

- Collector: `tools/r7e6_test_a_collector.py`
- Collector SHA-256: `b3abf6ea52d2b89031a84c686203c780d61c8aed4b2af997647c12592e8c781a`
- Manifest: `research/runtime/r7e6-test-a-plan-manifest.json`
- Manifest version: `R7E6A-TEST-A-COMMAND-SET-1`
- Manifest SHA-256: `39105acfae65cc05804bcab7d23fc7ab5a139e7f716d371787669b20d1da6a57`
- Exact target path: `/data/local/tmp/claritylink_target_diag_r7e6a_4b91c27e6d3a508f`
- ARMv7 artifact: 7,904 bytes; SHA-256 `9e20d1ad715be6c9974f9a89e1aa310283bc128f87350fb05cb224b8e247c063`; MD5 `6137a693a77646aaf9a4cf0f351731d4`
- Staging copy: mode `0555`, byte-identical, same SHA-256 and MD5; expected remote mode `0555`
- Package has no target `chmod`, external `ps`/`kill`, retry, fallback, root, display, USB, CarPlay, or Test B action.

The historical R7E6 authorization packet and manifest are preserved separately. The ADB legacy shell behavior and parser evidence do not constitute Honda proof. The host timeout remains 12 seconds, greater than the 4-second parent and 2-second child bounds; a host timeout is an anomaly and stops all further target commands.

## Verification

- Focused Test A collector fixtures: **42 passed**.
- Full repository suite: **1,024 passed, 15 skipped**.
- Self-locator smoke: **3 passed**.
- Simulator JavaScript checks: all configured checks passed.
- Repository health: passed after adding this report and correcting the curated links.
- Artifact audit: passed; ELF32 little-endian ARM EABI5; API17 imports resolved, zero unknown; `DT_NEEDED` remains `libdl.so`, `libc.so`.
- Staging comparison: byte-identical; mode `0555`; expected remote mode `0555`.
- `git diff --check`: passed.
- The collector default path printed `NOT_AUTHORIZED`; dry-run reported `adb_operations: 0`.

## ECC review record

ECC security-review and Python-testing guidance was applied to legacy-shell semantics, exact absence, path-bound digest parsing, process-state cleanup, authorization boundaries, artifact identity, and test coverage. A separate independent ECC reviewer was not available for this run; this report records a manual ECC-guided review, not an independent ECC approval.

See [current packet](../research/runtime/r7e6-test-a-authorization-packet.md), [manifest](../research/runtime/r7e6-test-a-plan-manifest.json), [decision](../research/runtime/r7e6-test-a-readiness-decision.md), [collector verification](../research/runtime/r7e6-test-a-collector-verification.md), and [API17 probe summary](../research/runtime/r7e6a-api17-absence-probe.md).
