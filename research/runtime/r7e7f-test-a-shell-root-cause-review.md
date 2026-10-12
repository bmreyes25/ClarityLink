# R7E7F Test A shell-construction and process-state review

## Decision

`R7E_TEST_A_RECOVERY_PACKAGE_READY` for separate read-only recovery authorization only. **Test A is not ready to retry.** The previous attempt may have left its diagnostic at the authorized temporary path, and neither its current file state nor process state is known. R7E7F made zero Honda ADB commands, zero Honda writes, zero pushes, zero Honda executable launches, and no cleanup.

## Baseline and previous failure evidence

Starting HEAD: `5436ef185ae17886937877b641c8e246dec3f4e5`. The original evidence is the ignored, private mode-0600 file `build/r7e6a/test-a/evidence/collector-failure-20261012T021444Z-b64f.json`; it was read without modification. It records one successful push, valid remote metadata and MD5, one `--version` invocation, then one process-absence command with host return code 0 and empty stdout/stderr. The collector stopped as `TEST_A_PROCESS_STATE_UNCERTAIN`. `--self-test`, cleanup, and final absence verification did not occur.

The failed record contains classifications only. It does not preserve the original diagnostic stdout/stderr, parsed PID values, or raw process-check command output. The diagnostic invocation returned host code 0 and nonempty stdout by classification; the process query returned host code 0 with empty stdout/stderr. These observations do **not** prove the guest exit status was zero, that either process was absent, or that the file remains present. The source ordering proves the collector had already accepted exactly one matching supervisor start/reap pair and valid distinct PID values before it made the process check. It computed the guest status marker but only validated it after the process check, so guest success was not confirmed.

The prior Test A authorization is consumed. Recovery and any future Test A require new, separate authorizations.

## Root cause

The old collector passed `adb shell sh -c <expression>` as separate host argv elements. ADB's legacy shell command handling joins the shell arguments with spaces; it does not preserve the host argv quoting as a remote argument boundary. AOSP documents this behavior in [`client/commandline.cpp`](https://android.googlesource.com/platform/packages/modules/adb/+/refs/heads/master/client/commandline.cpp). A historical AOSP regression test demonstrates the exact nested `sh -c` issue: [`adb/tests/test_adb.py`](https://android.googlesource.com/platform/system/core/+/5cba504/adb/tests/test_adb.py).

The resulting remote expression starts effectively as `sh -c test -d /proc/$$ ...`. The inner shell receives `test` as its command string; its following words become positional parameters. That `test` fails, short-circuiting the outer `&&` expression before the success sentinel. Legacy ADB may still return host status zero for a completed transport, so the empty guest output must be treated as failure. The R7E7E evidence matches this failure signature exactly. The root cause is confirmed by AOSP source, historical test, host reproduction, and isolated API17 reproduction.

## Correction and validation

The collector now invokes one full fixed remote expression as the sole argument after `adb shell`, without nested `sh -c`. The host uses `subprocess.run(argv, shell=False)`. Dynamic PID inputs must be positive decimal integers in `[2, 2147483647]`, without leading zeros and with distinct parent and child values. The remote shell expands `$$` and the command requires `/proc/$$`, `/proc/$$/stat`, and `/proc/self/stat` before checking exact PID absence and emitting the exact PID-bound sentinel. Empty/malformed/extra output, unexpected stderr, transport failures, timeouts, visible target PIDs, or absent positive controls fail closed. No process is signaled.

Local POSIX regression: old joined command returns without the sentinel; the corrected command shape is asserted as one argv element. API17 validation used the project's isolated Android 4.2.2/API17 x86 emulator and a dedicated one-device ADB server. The original malformed invocation produced host rc 0 with empty stdout/stderr. The corrected invocation produced exactly `R7E6_PIDS_ABSENT:2000000001:2000000002` plus newline, host rc 0. Remote `$$` expanded to a numeric guest PID. A live PID and a failed procfs positive control both blocked the sentinel. The emulator, dedicated ADB server, and temporary AVD were removed; cleanup failures: zero. Private raw probe evidence: `build/r7e6/runs/api17-shell-construction-b9ec6acc460d.json` (mode 0600). No physical device was used.

Failure evidence now stores redacted host argv, operation IDs, bounded stdout/stderr, exit classification, guest status marker report, parsed parent/child IDs, lifecycle counts, procfs/sentinel classifications, and cleanup eligibility in a mode-0600 local file. Raw Honda identifiers are not recorded. When process absence fails, guest status is labeled reported but not confirmed; cleanup remains prohibited.

## Identity and artifact

- Collector SHA-256: `acee02afd1eaef3aab5b4d4b24ded8044fce67e6461c1d4883b552c87465deb5`
- Manifest: `R7E7F-TEST-A-COMMAND-SET-5`
- Manifest SHA-256: `20e93f4692e423851b1195d7c52db1c42e5088126faee2db8c993622611ab6c9`
- ARMv7 artifact SHA-256: `9e20d1ad715be6c9974f9a89e1aa310283bc128f87350fb05cb224b8e247c063`
- ARMv7 artifact MD5: `6137a693a77646aaf9a4cf0f351731d4`
- Size/mode: 7,904 bytes / `0555`; canonical and staging copies are unchanged.
- Exact prior remote path: `/data/local/tmp/claritylink_target_diag_r7e6a_4b91c27e6d3a508f`.

The manifest binds the collector hash and its command plan. The package is a recovery-preparation package; the Test A authorization packet and prior authorization are not valid for it.

## Review and limits

ECC security-review, Python-testing, and Android compatibility guidance were applied manually. Independent ECC review was unavailable; no independent approval is claimed. The corrected transport was validated on API17 x86, not on the Honda. Current Honda file state, Android boot continuity, and process state remain unknown. The failure evidence lacks the old PIDs, so those IDs cannot be used as current identity claims. PID reuse across any reboot is not a process identity proof.

The vehicle does not need to remain powered during this offline milestone. Do not contact the Honda from R7E7F. Next action: obtain separate explicit authorization for the bounded Phase R read-only recovery inspection, then stop and review its results before considering any independently authorized cleanup. Test A must not be retried until recovery is resolved.

## Verification summary

- Focused collector suite: 87 passed.
- Full repository suite: 1,069 passed, 15 skipped.
- Self-locator smoke: 3 passed.
- Simulator checks: all configured checks passed.
- Repository health: 824 Markdown files; zero broken curated links; passed.
- `git diff --check`: passed.
- Collector dry run: `DRY_RUN_NO_ADB`, zero ADB operations; command list contains the corrected one-argument process checks.
- Artifact checker: passed; canonical mode `0755`, staging mode `0555`, 7,904 bytes, identical bytes.
- Pinned API17 import audit: all 25 undefined ARM imports present in API17 `libc.so`/`libdl.so`; unknown imports: zero.
- Offline CI and CodeQL must still be verified on the final pushed HEAD.
