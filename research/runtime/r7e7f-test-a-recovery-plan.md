# R7E7F prior Test A recovery plan — Phase R only is proposed

## Why recovery is needed

The previous Test A successfully pushed and verified the 7,904-byte diagnostic at `/data/local/tmp/claritylink_target_diag_r7e6a_4b91c27e6d3a508f`, invoked `--version` once, then stopped when the process-absence response was empty. It did not run `--self-test`, attempt cleanup, or verify final absence. The original private failure evidence is `build/r7e6a/test-a/evidence/collector-failure-20261012T021444Z-b64f.json`. It does not contain raw command output or PID values. The file and process states now are unknown.

The old process query was malformed by nested `adb shell sh -c` argument joining. R7E7F corrected and offline-tested that collector behavior, but this correction does not authorize use of the collector on the Honda or establish what remains there.

## Package reference

Artifact SHA-256 `9e20d1ad715be6c9974f9a89e1aa310283bc128f87350fb05cb224b8e247c063`, MD5 `6137a693a77646aaf9a4cf0f351731d4`, 7,904 bytes. Prior exact path: `/data/local/tmp/claritylink_target_diag_r7e6a_4b91c27e6d3a508f`. Original Test A collector/manifest identities are recorded in the private failure file and historical R7E7D packet. Current R7E7F collector SHA-256 `acee02afd1eaef3aab5b4d4b24ded8044fce67e6461c1d4883b552c87465deb5`; manifest `R7E7F-TEST-A-COMMAND-SET-5`, SHA-256 `20e93f4692e423851b1195d7c52db1c42e5088126faee2db8c993622611ab6c9`. These identities identify the offline recovery package and do not themselves authorize Honda access.

## Phase R — read-only inspection (requires a new separate authorization)

Purpose: inspect only the previously transferred exact path and gather the minimum facts needed for a later safety decision. The operator must freshly confirm stationary/safely parked status, booted head unit, normal cluster/no unexpected warnings, exact intended target, stable already-configured ADB connection, and exclusive ADB window. Require exactly one intended target in one inventory. Do not connect, disconnect, scan, restart ADB, or reconfigure transport.

Proposed collector-reviewed read-only sequence, using only the exact selected serial:

1. Verify the frozen local recovery-plan identities and the exact target inventory.
2. Capture `/data/local/tmp` metadata only if required to establish the fixed path context.
3. Query `ls -ld` for the exact executable path. Accept only a narrowly parsed absent result or a single regular-file metadata result; anything else stops.
4. If and only if the exact regular file exists with expected `shell:shell`, size 7904, and mode `0555`, query MD5 for that exact path and compare to the artifact identity. Do not execute it.
5. Stop. Preserve raw stdout/stderr, status, timestamp, and redacted command argv locally with restrictive permissions. No second observation, retry, file read beyond the approved exact hash, process enumeration, `ps`, signal, or cleanup.

Do not claim process status from stale PIDs. The original PIDs are absent from the failure record. Do not infer that a normal vehicle power-off rebooted Android or removed the file. If boot identity is not independently established within this authorized scope, mark it unknown. A path absent result proves only absence at that observation time. Any timeout, ambiguity, mismatch, unexpected file, or transport anomaly ends Phase R without further target commands.

### Phase R authorization template — read-only only

```text
CLARITYLINK R7E7F — EXPLICIT PHASE R READ-ONLY RECOVERY AUTHORIZATION

I authorize one read-only inspection of the prior Test A diagnostic at:
/data/local/tmp/claritylink_target_diag_r7e6a_4b91c27e6d3a508f

Purpose: determine whether that exact path is absent or contains the
previously transferred diagnostic, and record its exact metadata and MD5
if the file is present and the metadata gate passes.

I authorize only one target inventory and the frozen exact-path read-only
metadata/hash observations in the reviewed Phase R plan. No executable
transfer or execution is authorized. No deletion or other write is
authorized. No process enumeration, ps, kill, killall, pkill, root, su,
transport reconfiguration, retry, fallback, Test A, or Test B is authorized.

I will freshly confirm the vehicle is stationary and safely parked, display
fully booted, cluster normal, no unexpected warnings, intended already-
connected Honda target, stable connection, and exclusive ADB window. I will
not issue manual ADB commands during the observation.

I understand any timeout, identity mismatch, unexpected metadata, or
uncertain result means stop immediately and preserve evidence. This
authorization expires after the one read-only inspection and does not
authorize cleanup or Test A.
```

## Phase C — conditional exact-path cleanup (not authorized)

No cleanup is authorized by this plan or the Phase R template. Consider a separate Phase C proposal only after Phase R results are reviewed. Proceed to a future authorization request only if the exact path contains one regular file whose mode, owner/group, size, and content MD5 all match the known transferred artifact; the target identity and current process-safety basis are established without broad enumeration or stale PID assumptions; no conflicting identity or material uncertainty remains; and the evidence review supports removal. If any criterion fails, decision is NO-GO and do not delete.

If separately authorized after review, the proposed scope is one `/system/bin/rm` invocation for the exact path, followed by one exact-path ENOENT verification. No wildcard, directory cleanup, retry, fallback, diagnostic execution, chmod, root, or Test A. A timeout or uncertain result stops; do not claim cleanup. This is only a proposed conditional plan and is not executable authorization.

## Boundaries and next step

The corrected collector must not be used to initiate Test A during recovery. After Phase R, stop and present sanitized results. Any cleanup requires a separate explicit Phase C authorization. Any future Test A requires a new authorization bound to its eventual exact package and a proven safe recovery state. Test B remains separately unauthorized. The vehicle need not remain powered for offline work.
