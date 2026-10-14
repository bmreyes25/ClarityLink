# R7E7F Test A package — NOT AUTHORIZED; recovery required

## Current state

The previous Test A attempt pushed and verified the diagnostic, invoked `--version` once, then stopped because the process-absence check returned empty output. It did not run `--self-test`, attempt cleanup, or confirm final file absence. The exact remote file and process states remain unknown. The previous Test A authorization is consumed. **Do not retry Test A.**

R7E7F traced and reproduced the nested legacy ADB shell defect and corrected the collector offline. The package identities below freeze that corrected collector for future review; they authorize no Honda operation. R7E7F itself made zero Honda ADB commands, writes, pushes, executable launches, or cleanup actions.

- Repository: `bmreyes25/ClarityLink`, PR #19
- Baseline HEAD: `5436ef185ae17886937877b641c8e246dec3f4e5`
- Collector: `tools/r7e6_test_a_collector.py`
- Collector SHA-256: `acee02afd1eaef3aab5b4d4b24ded8044fce67e6461c1d4883b552c87465deb5`
- Manifest: `research/runtime/r7e6-test-a-plan-manifest.json`
- Manifest version: `R7E7F-TEST-A-COMMAND-SET-5`
- Manifest SHA-256: `20e93f4692e423851b1195d7c52db1c42e5088126faee2db8c993622611ab6c9`
- Artifact: `build/r7e6/test-a/claritylink-target-diag`, 7,904 bytes, mode `0555`
- Artifact SHA-256: `9e20d1ad715be6c9974f9a89e1aa310283bc128f87350fb05cb224b8e247c063`
- Artifact MD5: `6137a693a77646aaf9a4cf0f351731d4`
- Prior exact destination: `/data/local/tmp/claritylink_target_diag_r7e6a_4b91c27e6d3a508f`

## Next action: separate Phase R authorization

Use [the R7E7F recovery plan](r7e7f-test-a-recovery-plan.md) for a new, explicit **read-only Phase R authorization only**. It is limited to one target inventory and exact-path metadata, plus exact MD5 only if expected file metadata passes. It does not authorize cleanup, diagnostic execution, Test A, or Test B. Stop after Phase R and review its results. The previously transferred executable may still exist.

Conditional Phase C cleanup is not authorized. It may be considered only after Phase R evidence is reviewed, file identity is confirmed, and process-safety uncertainty is resolved; it requires its own separate authorization. If uncertainty remains, the decision is NO-GO.

## Root cause and validation

Legacy ADB joins `adb shell` arguments into a remote shell command. The former `adb shell sh -c <expression>` therefore lost the intended inner-shell command boundary. The nested command short-circuited before the PID sentinel, while host transport status remained zero. AOSP's command construction and historical escaping test support this behavior. The exact failure signature was reproduced on isolated Android 4.2.2/API17 x86: old invocation returned host status 0 with empty output; the corrected one-argument remote expression emitted its exact sentinel. The fix retains procfs positive controls and fail-closed exact output checks. See [R7E7F review](r7e7f-test-a-shell-root-cause-review.md).

This package is **not a Test A execution authorization** and must not be used to run the collector on the Honda. Independent ECC review was unavailable; manual ECC-guided review is documented. The vehicle does not need to remain powered during the offline milestone.

## Historical package

The previous R7E7D packet is preserved at [r7e6-test-a-authorization-packet-r7e7d-historical.md](r7e6-test-a-authorization-packet-r7e7d-historical.md). It is historical and its authorization is consumed.
