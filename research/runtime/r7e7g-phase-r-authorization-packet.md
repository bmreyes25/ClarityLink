# R7E7G Phase R read-only recovery packet — draft, inactive

This document prepares a **future, separate authorization**. It does not authorize a command now. The previous Test A authorization is consumed. Phase R is a single read-only observation of the exact prior executable path. It cannot establish current process safety or authorize cleanup.

## Frozen package

- Repository/PR: `bmreyes25/ClarityLink` / PR #19.
- Collector: `tools/r7e7g_phase_r_collector.py`; SHA-256 `de230c8a97aa06ea5134bc11a0902d59b86eee437bec913e273e5c2fb3edfc15`.
- Manifest: `research/runtime/r7e7g-phase-r-manifest.json`, version `R7E7G-PHASE-R-READ-ONLY-1`; SHA-256 `9018f587f86dc45079e25bc81450de6381932991ae9b0bfdcc838c51b9f71278`.
- Imported Test A helper source: `tools/r7e6_test_a_collector.py`; frozen SHA-256 `acee02afd1eaef3aab5b4d4b24ded8044fce67e6461c1d4883b552c87465deb5`. Phase R checks this dependency before ADB use.
- Referenced prior diagnostic: SHA-256 `9e20d1ad715be6c9974f9a89e1aa310283bc128f87350fb05cb224b8e247c063`, MD5 `6137a693a77646aaf9a4cf0f351731d4`, 7904 bytes, mode `0555`, `shell:shell`.
- Exact path: `/data/local/tmp/claritylink_target_diag_r7e6a_4b91c27e6d3a508f`.
- Timeout: 12 seconds per command; zero retries and fallbacks.

The package must be re-hashed and reviewed against the final pushed HEAD before any future use. A changed collector or manifest invalidates these values and this draft.

## Proposed command sequence

The collector first verifies its own source/manifest hashes and the operator gates locally. It then issues the following commands, in order, through the specified ADB executable. `<EXACT_SERIAL>` is the newly confirmed exact target selector; every target command uses `-s` with that selector.

```text
adb version
adb devices
adb -s <EXACT_SERIAL> shell ls -ld /data/local/tmp
adb -s <EXACT_SERIAL> shell ls -ld /data/local/tmp/claritylink_target_diag_r7e6a_4b91c27e6d3a508f
```

If and only if the exact path is one regular file with expected mode, owner, group, size, and basename, the collector issues one more command:

```text
adb -s <EXACT_SERIAL> shell /system/bin/md5 /data/local/tmp/claritylink_target_diag_r7e6a_4b91c27e6d3a508f
```

It stops after classifying `EXACT_PATH_ABSENT`, `EXPECTED_REGULAR_FILE_PRESENT`, `UNEXPECTED_FILE_STATE`, or `UNKNOWN_OR_AMBIGUOUS_STATE`. A mismatched MD5 is `UNEXPECTED_FILE_STATE`. Unexpected inventory, parent metadata, permission errors, empty output, malformed listing, timeout, and transport anomalies stop without further commands. Private evidence is recorded under `build/r7e7g/phase-r/evidence/` with mode 0600 and a redacted serial.

No executable transfer, execution, file deletion, process enumeration, signal, root, `su`, transport reconfiguration, retry, Test A, or Test B is in this packet. The dry run and default mode issue zero ADB calls.

## Operator conditions for later authorization

Before using a reviewed final package, freshly confirm the vehicle is stationary and safely parked; display fully booted; cluster normal with no unexpected warnings; one exact intended already-connected target; stable transport; and an exclusive ADB window. Do not connect, disconnect, scan, restart ADB, or issue manual ADB commands during collection. Any identity mismatch or uncertain response ends the inspection. Preserve the private evidence and present a sanitized result for review.

## Phase R authorization template — unsubmitted

```text
CLARITYLINK R7E7G — SINGLE-USE PHASE R READ-ONLY AUTHORIZATION

I authorize one read-only inspection of the exact prior Test A path:
/data/local/tmp/claritylink_target_diag_r7e6a_4b91c27e6d3a508f

I have reviewed the final repository HEAD, Phase R collector SHA-256,
Phase R manifest SHA-256, imported Test A helper SHA-256, exact commands above, stop conditions, and
current operator conditions. I will provide the exact intended target
selector only after verifying a single already-connected target.

This authorization covers one inventory, one parent metadata observation,
one exact-path metadata observation, and one exact-path MD5 observation
only if the expected regular-file metadata passes. It expires after this
one inspection. It does not authorize any write, diagnostic launch,
cleanup, process enumeration, transport reconfiguration, retry, Test A,
or Test B. Uncertainty means stop and preserve evidence.
```
