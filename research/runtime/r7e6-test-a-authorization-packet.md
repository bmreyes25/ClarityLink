# R7E6 Test A authorization packet — NOT AUTHORIZED

## Decision and identity

Package readiness: `R7E_TEST_A_EXECUTION_PACKAGE_READY`. Test A remains `NOT_AUTHORIZED`; this packet is a review artifact and does not grant permission to run it.

- Collector: `tools/r7e6_test_a_collector.py`
- Collector SHA-256: `5837624209be870b60027041235428e5839dcf4b85055bbdfd83cd759794235e`
- Manifest: `research/runtime/r7e6-test-a-plan-manifest.json`
- Manifest SHA-256: `86f270be05e166e2a54738e186a350fcd3d9f5f8f8b804de4b668b18ffdc7205`
- Canonical ARMv7/API17 artifact size: 7,904 bytes
- Canonical artifact SHA-256: `9e20d1ad715be6c9974f9a89e1aa310283bc128f87350fb05cb224b8e247c063`
- Canonical artifact MD5: `6137a693a77646aaf9a4cf0f351731d4`
- Local staging copy: `build/r7e6/test-a/claritylink-target-diag`, mode `0555`, byte-identical to the canonical artifact.
- Exact remote path: `/data/local/tmp/claritylink_target_diag_r7e6_7f1a3c9d2b6e40a8`
- Expected Honda target metadata: regular file, `shell:shell`, exact size 7,904, mode `0555` (`-r-xr-xr-x`), executable and not writable.

The API17 x86 emulator had `root:root` ownership for its test transfer. That emulator-specific owner is recorded in private runtime evidence and is not used as the Honda expectation.

## What Test A does

Test A uses one exact ADB target selected by the operator. It checks the host ADB version and target inventory, confirms `/data/local/tmp` metadata and exact-path absence, performs one push, checks exact file metadata and MD5, runs the exact executable with `--version` and `--self-test`, verifies both reported parent/child PID pairs are absent, removes only the exact artifact path, verifies exact absence, and asks the operator to directly observe unchanged stock vehicle state.

The collector requires all of these pre-execution operator gates: vehicle stationary and safely parked; center display fully booted; cluster normal; no unexpected warnings; exact directly observed power state; exact directly observed audio state; and an exclusive ADB window. After cleanup it requires direct confirmation `STOCK_STATE_UNCHANGED`.

## Frozen command sequence

All target commands after inventory use `-s <EXACT_SERIAL>`. The actual serial is supplied only at a future authorized invocation and is not stored in this packet or its tracked evidence.

1. `adb version` (must match frozen ADB `37.0.1-15733141`).
2. `adb devices` (must contain exactly the supplied serial in `device` state).
3. `adb -s <EXACT_SERIAL> shell ls -ld /data/local/tmp`.
4. `adb -s <EXACT_SERIAL> shell test ! -e /data/local/tmp/claritylink_target_diag_r7e6_7f1a3c9d2b6e40a8`.
5. Exactly one `adb -s <EXACT_SERIAL> push build/r7e6/test-a/claritylink-target-diag /data/local/tmp/claritylink_target_diag_r7e6_7f1a3c9d2b6e40a8`.
6. Exact `ls -l` metadata check and `/system/bin/md5` check.
7. `<EXACT_PATH> --version; echo __R7E6_STATUS:$?`.
8. Exact child/parent `/proc/<PID>` absence check from the two PIDs directly reported by the supervisor.
9. `<EXACT_PATH> --self-test; echo __R7E6_STATUS:$?`.
10. Repeat the exact child/parent absence check.
11. `/system/bin/rm <EXACT_PATH>`.
12. Exact absence check.

There is no target `chmod`, external `ps`, external `kill`, retry, wildcard, alternate path, or fallback. The collector uses a 12-second host timeout for target commands (greater than the proven 4-second parent bound) and a 30-second transfer timeout. The frozen maximum target-command wall budget is 174 seconds, excluding operator observations.

## Rollback and stop rules

- Normal completion: one exact `/system/bin/rm <EXACT_PATH>` followed by exact absence verification.
- Non-timeout failure after a push attempt, before cleanup begins: one exact-path `/system/bin/rm` attempt and one exact absence check. No repeated cleanup attempt.
- Host timeout: classify `TEST_A_WATCHDOG_OR_TRANSPORT_ANOMALY`; stop and preserve local evidence. Issue no more target command, do not use `ps`/`kill`, do not retry, and require a separate recovery review.
- Any uncertain identity, target count, path state, metadata, digest, status, process state, cleanup, or vehicle state: fail closed and do not continue.

## Success means

Success establishes only that this exact ARMv7/API17 executable transferred with the expected identity and permissions, dynamically loaded and started, returned from both bounded modes, reaped its exact child, left the exact processes absent, was removed exactly, and the operator directly observed unchanged stock vehicle state.

It does not test or establish Display1, Presentation, visual output, framebuffer or SurfaceFlinger behavior, CarPlay, MFi, iAP2, USB ownership, root, jmcs changes, vehicle interface access, or Test B.

## Separate authorization requirement

The collector prints `NOT_AUTHORIZED` by default; `--dry-run` performs zero ADB operations. `--execute-authorized-test-a` is a software gate, not authorization. Before any execution, the user must separately and explicitly authorize Test A for these exact collector and manifest hashes, and the operator must satisfy the stated gates. No authorization was given in R7E6. Test B cannot start automatically.
