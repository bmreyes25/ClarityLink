# R7E6A Test A authorization packet — NOT AUTHORIZED

## Decision and exact package identity

**Package readiness:** `R7E_TEST_A_EXECUTION_PACKAGE_READY` after the R7E6A collector corrections. This packet does not grant execution permission. Test A remains **NOT_AUTHORIZED** and **NOT_EXECUTED**.

- Repository: `bmreyes25/ClarityLink`, PR #19
- R7E6A manifest version: `R7E6A-TEST-A-COMMAND-SET-1`
- Collector: `tools/r7e6_test_a_collector.py`
- Collector SHA-256: `b3abf6ea52d2b89031a84c686203c780d61c8aed4b2af997647c12592e8c781a`
- Manifest: `research/runtime/r7e6-test-a-plan-manifest.json`
- Manifest SHA-256: `39105acfae65cc05804bcab7d23fc7ab5a139e7f716d371787669b20d1da6a57`
- ARMv7/API17 artifact size: 7,904 bytes
- Artifact SHA-256: `9e20d1ad715be6c9974f9a89e1aa310283bc128f87350fb05cb224b8e247c063`
- Artifact MD5: `6137a693a77646aaf9a4cf0f351731d4`
- Staging copy: `build/r7e6/test-a/claritylink-target-diag`, mode `0555`, byte-identical to canonical artifact
- Exact remote path: `/data/local/tmp/claritylink_target_diag_r7e6a_4b91c27e6d3a508f`
- Expected remote state: regular `shell:shell`, 7,904 bytes, mode `0555` (`-r-xr-xr-x`), executable and not writable
- Historical R7E6 packet and manifest are preserved in the `*-historical` files.

GitHub checks were verified on the prior package head `fad39c42fc58638afd5d003deee3e4d97df89c58`: Offline CI, CodeQL workflow, and all five configured language jobs were successful; Advanced Security reported no new alerts in changed code. The first pushed R7E6A head `3c588e254539f802126ea6fdd0bcbe1dd94bd069` passed Offline CI, aggregate CodeQL with no new alerts, and all five configured CodeQL language jobs. The final documentation-only commit must also be checked on its exact GitHub head before any separate authorization.

## Test A scope and operator gates

Test A checks only whether the exact ARMv7/API17 diagnostic transfers intact, has the expected non-writable executable mode, starts as ordinary shell, returns from `--version` and bounded `--self-test`, reaps its exact child, can be removed exactly, and leaves observed stock vehicle state unchanged.

Before any separately authorized run, require: stationary and safely parked; center display fully booted; cluster normal; no unexpected warnings; exact direct power-state and audio-state observations; and an exclusive ADB window. Afterward require direct observation `STOCK_STATE_UNCHANGED`.

## Frozen command sequence

Commands use the supplied exact serial after inventory. The collector requires ADB `37.0.1-15733141` and exactly one device in `device` state.

1. `adb version`
2. `adb devices`
3. `adb -s <EXACT_SERIAL> shell ls -ld /data/local/tmp`
4. `adb -s <EXACT_SERIAL> shell ls -ld /data/local/tmp/claritylink_target_diag_r7e6a_4b91c27e6d3a508f` — require the exact single-line ENOENT output described below.
5. One `adb -s <EXACT_SERIAL> push build/r7e6/test-a/claritylink-target-diag /data/local/tmp/claritylink_target_diag_r7e6a_4b91c27e6d3a508f`
6. Exact `ls -l` metadata and `/system/bin/md5` verification.
7. `<EXACT_PATH> --version; echo __R7E6_STATUS:$?`
8. Exact `/proc/<PID>` absence check for the exact parent and child PIDs reported by the diagnostic.
9. `<EXACT_PATH> --self-test; echo __R7E6_STATUS:$?`
10. Repeat the exact parent/child absence check.
11. `/system/bin/rm <EXACT_PATH>`
12. `adb -s <EXACT_SERIAL> shell ls -ld <EXACT_PATH>` — require the exact single-line ENOENT output.

There is no `test ! -e` absence gate. Android 4.2.2 raw ADB shell can return host status 0 with empty output after a guest `test` failure; empty output is not evidence of absence. The collector accepts only one exact output line naming the frozen path and `No such file or directory`, with host return code 0 or 1. It rejects empty, extra, mismatched, permission, command-not-found, and all other output. The API17 emulator probe observed the host-zero/empty-output case and verified exact ENOENT for absent paths, while regular files, symlinks, and directories were rejected as absent. See the [probe summary](r7e6a-api17-absence-probe.md).

Remote MD5 must be exactly one line containing the expected 32-hex digest, one space, and the exact frozen remote path. Wrong-path, multiple, truncated, malformed, or noisy output fails closed.

## Process and rollback rules

The diagnostic retains its 2-second child and 4-second parent bounds; each host target command has a 12-second timeout, and the push timeout is 30 seconds. No external `ps`, `kill`, `killall`, `pkill`, root, or `su` is used.

- Before a diagnostic starts, a post-push non-timeout failure permits one exact-path `rm` and one exact ENOENT check.
- After a diagnostic starts, cleanup is permitted only after the collector verifies the exact matching supervisor start/reap records and confirms both reported PIDs absent from `/proc`.
- If process identity or absence is uncertain, do not remove the executable. Preserve the private failure record and require a separate recovery review.
- Any host timeout is `TEST_A_WATCHDOG_OR_TRANSPORT_ANOMALY`: stop, preserve evidence, and issue no more target command. No retry or fallback.
- Cleanup failure or uncertain final ENOENT means no success claim.

The default collector path prints `NOT_AUTHORIZED`; `--dry-run` performs zero ADB operations. The `--execute-authorized-test-a` flag is only a software gate and is not user authorization. A separate explicit user authorization must bind these exact collector, manifest, and artifact identities.

## Success and exclusions

Success establishes transfer and dynamic loading of this artifact, both bounded diagnostic modes, exact process completion, exact-path removal and final ENOENT, and direct unchanged-stock observation. It does not test Display1, Presentation, visual output, framebuffer or SurfaceFlinger behavior, CarPlay, MFi, iAP2, USB ownership, root, jmcs changes, vehicle interfaces, or Test B. Test B cannot start automatically.

No Honda command or physical Android contact occurred while preparing this package.
