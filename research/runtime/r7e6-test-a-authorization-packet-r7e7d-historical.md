# R7E7D Test A authorization packet — NOT AUTHORIZED

## Package status

R7E7D reviewed actual historical Android 4.2.2 output and corrected the MD5 separator parser and mismatch between the manifest's relative push path and the collector's absolute execution path. Parent metadata now supports the observed legacy listing, and malformed inventory rows fail closed. This packet does not authorize execution. Offline CI and aggregate CodeQL passed on exact head `75c1fb332fd2a187a62a9ab29274484667c1c2d2`; all five configured CodeQL language jobs passed: [Offline CI](https://github.com/bmreyes25/ClarityLink/actions/runs/38193380088), [CodeQL](https://github.com/bmreyes25/ClarityLink/actions/runs/38193380092). This package now awaits a fresh user authorization.

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

## New authorization statement — copy, complete, and submit separately

```text
CLARITYLINK R7E7E — EXPLICIT TEST A AUTHORIZATION

I explicitly authorize Test A ONLY on my 2018 Honda Clarity using:

Repository: bmreyes25/ClarityLink, PR #19
Exact HEAD: 75c1fb332fd2a187a62a9ab29274484667c1c2d2
Collector: tools/r7e6_test_a_collector.py
Collector SHA-256: 7cae443313ebe0d27d67bb08b32b140897c3b4d33f7e312d3323d70f37b8f129
Manifest: research/runtime/r7e6-test-a-plan-manifest.json
Manifest version: R7E7D-TEST-A-COMMAND-SET-4
Manifest SHA-256: 553f3dcf44e51bf91433838fccbcdfe6ec2b5af84608de61c6228daa96eb6b5e
Artifact: build/r7e6/test-a/claritylink-target-diag
Artifact SHA-256: 9e20d1ad715be6c9974f9a89e1aa310283bc128f87350fb05cb224b8e247c063
Artifact MD5: 6137a693a77646aaf9a4cf0f351731d4
Artifact size: 7904 bytes
Staging mode: 0555; expected remote mode: 0555
Exact remote path: /data/local/tmp/claritylink_target_diag_r7e6a_4b91c27e6d3a508f

I authorize the collector to verify these identities and host ADB version,
inventory the already-connected target, verify parent metadata and exact
path absence, perform exactly one push, verify remote file metadata and
MD5, execute --version once and --self-test once, verify the frozen exact
supervisor/child lifecycle and procfs controls, remove only the exact
remote path when cleanup conditions pass, and verify exact final absence.
I authorize only the frozen command plan and approved failure cleanup.

Child deadline: 2 seconds. Parent deadline: 4 seconds.
Host command timeout: 12 seconds. Push timeout: 30 seconds.
No retry, fallback, target chmod, connection reconfiguration, or additional
target command is authorized. A host timeout or uncertain process state
requires an immediate stop; do not issue further target commands or claim
cleanup/restoration. If process state is uncertain, leave the executable
in place and require a separately reviewed recovery authorization.

Before execution I will directly confirm: stationary and safely parked;
center display fully booted; cluster normal; no unexpected warnings;
exact observed power state: <OBSERVATION>; exact observed audio state:
<OBSERVATION>; already-connected intended Honda target; stable connection;
exclusive ADB window with no other terminal, script, or Codex process using
ADB, and I will issue no manual ADB commands during the test.

I understand Test A success is only TEST_A_PASS_FOR_REVIEW. It does not
authorize Test B or establish Display1, Presentation, cluster rendering,
CarPlay, MFi, USB/iAP2, or simultaneous streams.

I DO NOT authorize Test B; Display1 or Presentation manipulation; screen
rendering; CarPlay or MFi operations; USB/iAP2 changes; root or su; jmcs or
system-partition changes; APK installation; binary patching; startup
configuration changes; network reconfiguration; extra executable
transfers; process-name killing; retries; fallbacks; or unrelated vehicle
operations.

My exact currently observed Honda ADB serial is: <SERIAL>

I have rechecked that all package identities above match the current frozen
package and authorize R7E7E Test A ONLY.
```

## Future execution handoff (not run during preparation)

After the separate authorization above and fresh operator confirmations, verify the exact HEAD and hashes again, then run only the frozen collector from the repository root:

```sh
python3 tools/r7e6_test_a_collector.py \
  --execute-authorized-test-a \
  --authorized-collector-sha256 "7cae443313ebe0d27d67bb08b32b140897c3b4d33f7e312d3323d70f37b8f129" \
  --authorized-manifest-sha256 "553f3dcf44e51bf91433838fccbcdfe6ec2b5af84608de61c6228daa96eb6b5e" \
  --serial "<EXACT_OPERATOR_CONFIRMED_HONDA_SERIAL>" \
  --stationary --parked --display-booted --cluster-normal --no-warnings \
  --exclusive-adb-window \
  --power-state "<EXACT_DIRECT_OBSERVATION>" \
  --audio-state "<EXACT_DIRECT_OBSERVATION>"
```

The execution task must preserve raw evidence privately, stop on any identity mismatch/timeout/uncertain process state, issue no retries or fallback commands, and stop after Test A. Test B remains separately unauthorized.
