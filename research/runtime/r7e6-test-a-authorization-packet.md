# R7E7D Test A authorization packet — NOT AUTHORIZED

## Package status

R7E7D reviewed actual historical Android 4.2.2 output and corrected the MD5 separator parser and mismatch between the manifest's relative push path and the collector's absolute execution path. Parent metadata now supports the observed legacy listing, and malformed inventory rows fail closed. This packet does not authorize execution. Final exact-head offline and hosted verification is required.

- Repository: `bmreyes25/ClarityLink`, PR #19
- Collector: `tools/r7e6_test_a_collector.py`
- Collector SHA-256: `7cae443313ebe0d27d67bb08b32b140897c3b4d33f7e312d3323d70f37b8f129`
- Manifest: `research/runtime/r7e6-test-a-plan-manifest.json`
- Manifest version: `R7E7D-TEST-A-COMMAND-SET-4`
- Manifest SHA-256: `553f3dcf44e51bf91433838fccbcdfe6ec2b5af84608de61c6228daa96eb6b5e`
- Artifact path: `build/r7e6/test-a/claritylink-target-diag`
- Artifact size: 7904 bytes
- Artifact SHA-256: `9e20d1ad715be6c9974f9a89e1aa310283bc128f87350fb05cb224b8e247c063`
- Artifact MD5: `6137a693a77646aaf9a4cf0f351731d4`
- Staging mode: `0555`; remote expected mode: `0555`, owner/group `shell:shell`
- Exact remote path: `/data/local/tmp/claritylink_target_diag_r7e6a_4b91c27e6d3a508f`

## Frozen command sequence

The collector uses ADB `37.0.1-15733141`, exact supplied serial, exactly one connected target, and only this sequence:

1. `adb version`
2. `adb devices`
3. `adb -s <EXACT_SERIAL> shell ls -ld /data/local/tmp` — one line, exact mode `drwxrwx--x`, owner/group `shell:shell`, final token `tmp` or `/data/local/tmp`.
4. `adb -s <EXACT_SERIAL> shell ls -ld <EXACT_REMOTE_PATH>` — exact path-specific ENOENT only.
5. One push of `build/r7e6/test-a/claritylink-target-diag` to the exact remote path. The collector runs from the repository root; the relative source path is the same in manifest, execution, and transfer-output validation.
6. `ls -l` metadata — regular file, `-r-xr-xr-x`, `shell:shell`, exactly 7904 bytes and exact basename.
7. `/system/bin/md5 <EXACT_REMOTE_PATH>` — one 32-hex digest, one or two spaces, exact path; expected digest is `6137a693a77646aaf9a4cf0f351731d4`.
8. Execute `--version` once, then verify exact parent/child lifecycle, same-shell procfs controls, and exact PID absence marker.
9. Execute `--self-test` once, then repeat the same exact process checks.
10. Remove only the exact executable path and verify exact final ENOENT.
11. Obtain direct operator observation of stock state.

The preserved A0-WR push success appeared on stderr, which is included in the single-line parser. Its MD5 output contained two spaces before the path; the current parser accepts that observed format. The exact 7904-byte push output remains unobserved until separately authorized Test A and must match source, transfer count, `0 skipped`, and exact byte count.

## Timeouts, process state, and cleanup

- Child watchdog: 2 seconds; parent watchdog: 4 seconds.
- Host target command timeout: 12 seconds; push timeout: 30 seconds.
- No retries, fallback, target chmod, process-name matching, external kill, `ps`, root, or `su`.
- On any host timeout: stop and issue no more target commands.
- If process state is uncertain: stop, preserve evidence, and do not remove a potentially executing file.
- A single exact-path cleanup is allowed only for the frozen pre-execution failure case or after exact lifecycle completion and positive process absence.

## Required future operator conditions

The operator must freshly confirm the vehicle is stationary and safely parked; display fully booted; cluster normal; no unexpected warnings; exact directly observed power and audio states; intended Honda target and stable existing connection; and an exclusive ADB window with no other ADB use. Do not infer ACC/ON/READY. Do not leave the vehicle in accessory-only state for an extended period.

After success, directly inspect center display, cluster, warnings, audio, and stock responsiveness. Only a direct `STOCK_STATE_UNCHANGED` confirmation qualifies.

## Authorization boundary

R7E7B Test A and R7E7C read-only authorizations are consumed. R7E7D preparation, this packet, a dry run, CI, or prior vehicle observations do not authorize Test A. A new explicit user authorization must bind the final repository HEAD and every package identity above and must confirm current operator gates. Test B remains independently unauthorized.

A successful Test A would establish only that this executable transferred, ran its two bounded modes, met the process checks, was removed, and left directly observed stock state unchanged. It would not establish Display1, Presentation, cluster rendering, CarPlay, MFi, iAP2, USB integration, or Test B compatibility.
