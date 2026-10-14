# R7E7I Phase S read-only inspection packet — prepared, inactive

This packet is **not** authorization to contact the Honda. The prior Phase R authorization is consumed. Phase S needs a new single-use user message, a separately reviewed private clock-bound attestation, and fresh operator conditions. The current process state remains unknown. No Phase S, Phase C, Test A, or Test B command ran while preparing this packet.

## Frozen identities and prior evidence

- Repository `bmreyes25/ClarityLink`, PR #19. Starting R7E7I HEAD `0bc0defcaf79164745da304652f3945a131e5765`.
- Collector `tools/r7e7i_phase_s_collector.py` SHA-256: `9bec4ecd58b49e50b1d27cc0807c14ee7407397cb078918c129d8783291c0464`.
- Manifest `research/runtime/r7e7i-phase-s-manifest.json`, version `R7E7I-PHASE-S-READ-ONLY-1`, SHA-256: `bbd9afe14005ec6e3e68d6a5781232f538123aa04ce6a3932a697dd6789eb310`.
- Original private failure evidence SHA-256 `21e6551fde4498603dbfc9129aa4f32a61b0f0c7e89f3a70ba5035cfccee430e`; original host finish stamp `2026-10-12T02:14:44.929697+00:00`. It contains no old PIDs or boot ID.
- Reviewed private Phase R evidence SHA-256 `001e13ba7c5911a5d03e10114d6d8925cb3e3fa4c619b2ce2ba396bd1cae3ddd`; Phase R found the exact regular file, `0555`, `shell:shell`, 7904 bytes, matching remote MD5 `6137a693a77646aaf9a4cf0f351731d4`. Remote SHA-256 was not measured.
- The R7E7F recovery review commit `243ee18fbfa5dd53b64c1c414dade12740a415c8` describes the already-failed attempt. GitHub Actions run [38196454003](https://github.com/bmreyes25/ClarityLink/actions/runs/38196454003) on that head was created at `2026-10-12T02:36:36Z`. A reviewed 1800-second minimum historical error budget places the latest possible prior invocation after that server timestamp, with about eight minutes of additional guard. The inference depends on the review's chronology being accurate; no later relaunch is established by this fact.

## Current clock-bound attestation: required and absent

Before a future authorization, an independent reviewer must create `build/r7e7i/phase-s/clock-bound-attestation.json` as a private mode-0600 file and review its SHA-256. It must contain the exact schema below, with actual evidence in both basis fields. An empty assertion, a guessed error budget, or an expired bound is insufficient. The authorizing message must name its exact SHA-256. The collector checks the file hash and contents before any ADB operation. There is **no valid attestation in this milestone**.

```json
{
  "version": "R7E7I-CLOCK-BOUND-1",
  "old_evidence_sha256": "21e6551fde4498603dbfc9129aa4f32a61b0f0c7e89f3a70ba5035cfccee430e",
  "historical_clock_error_seconds": 1800,
  "current_clock_error_seconds": 60,
  "historical_basis": "Reviewed GitHub Actions run 38196454003 server createdAt and R7E7F review commit chronology; document uncertainty and no later known launch",
  "current_basis": "Replace with a fresh independent current UTC reference and its documented maximum error",
  "independent_reviewer": "Replace with actual reviewer",
  "valid_until_utc": "Replace with a short, reviewed UTC expiry"
}
```

The numbers in this example are illustrative. No one should create this file merely to satisfy the parser. The current-time basis must be fresh when Phase S would run. The collector requires each error bound between zero and 86,400 seconds and the historical bound at least 1800 seconds. A result can prove a later reboot only when the lower bound on current boot time exceeds the conservative upper bound on the prior invocation by more than one second.

## Exact proposed command sequence

Replace `<EXACT_CONFIRMED_HONDA_ADB_SERIAL>` only after fresh operator confirmation. The literal collector plan uses `<EXACT_SERIAL>` as a placeholder. No other target command or fallback is in scope.

1. `adb version` — require the frozen `37.0.1-15733141` host version response.
2. `adb devices` — require exactly one intended target in `device` state.
3. `adb -s <EXACT_CONFIRMED_HONDA_ADB_SERIAL> shell /system/bin/cat /proc/sys/kernel/random/boot_id`.
4. `adb -s <EXACT_CONFIRMED_HONDA_ADB_SERIAL> shell /system/bin/cat /proc/uptime`.
5. `adb -s <EXACT_CONFIRMED_HONDA_ADB_SERIAL> shell /system/bin/cat /proc/sys/kernel/random/boot_id`.

Every command has a 12-second host timeout. There are zero retries, fallbacks, target writes, signals, diagnostic launches, process scans, and cleanup commands. Any missing or malformed procfs source, nonzero return, unexpected stderr, target mismatch, timeout, clock step, or changed boot ID stops immediately without another target command. Raw command results remain in ignored, private mode-0600 local evidence with the serial redacted in argv; do not commit the evidence.

The two boot-ID reads test continuity *within this inspection*; there was no old boot ID to compare. Linux may generate the ID lazily on first read, so the command is read-only at the filesystem/ADB level while it may initialize kernel-internal ID state. `/proc/uptime` measures time since kernel boot without relying on the Honda's wall clock. The host timestamp and independently attested uncertainty bound provide the cross-session comparison. An unavailable `boot_id` is inconclusive; there is no fallback to `/proc/stat` or a process sweep.

## Decision and safety limit

- `PREVIOUS_PROCESS_TERMINATION_ESTABLISHED`: same current boot ID around a valid uptime reading, stable host clock during inspection, and conservative current boot lower bound later than the prior invocation upper bound. This proves the previous process could not survive that kernel reboot. It does **not** prove no later invocation, current process absence, file removal, or remote SHA-256.
- `PROCESS_POSSIBLY_ACTIVE`: readings are valid but the strict reboot inequality is not satisfied. No cleanup.
- `BOOT_CONTINUITY_UNKNOWN`: boot ID or uptime unavailable, empty, malformed, or otherwise insufficient. No cleanup.
- `PROCESS_EVIDENCE_CONFLICT`: boot IDs differ or the host clock changes relative to monotonic time. No cleanup.
- `INSPECTION_TIMEOUT`: any command exceeds 12 seconds. No retry or cleanup.
- `INSPECTION_IDENTITY_MISMATCH`: wrong package, ADB version, or target. No cleanup. Package mismatches stop before ADB.

Only the first result can **support considering** Phase C. Phase C also needs a separately reviewed current process/relaunch safety basis, fresh exact file identity and target confirmation, and a new single-use authorization.

## Future single-use user message template

The bracketed fields must be replaced with concrete reviewed values before submission. The template is intentionally inoperative until the private clock-bound attestation exists and its hash and expiry are verified.

The future operator's reviewed invocation is the frozen collector from the repository root, with only the confirmed serial and reviewed attestation hash substituted:

```text
python3 tools/r7e7i_phase_s_collector.py --dry-run
python3 tools/r7e7i_phase_s_collector.py \
  --execute-authorized-phase-s \
  --authorized-collector-sha256 9bec4ecd58b49e50b1d27cc0807c14ee7407397cb078918c129d8783291c0464 \
  --authorized-manifest-sha256 bbd9afe14005ec6e3e68d6a5781232f538123aa04ce6a3932a697dd6789eb310 \
  --authorized-clock-attestation-sha256 <EXACT_REVIEWED_PRIVATE_ATTESTATION_SHA256> \
  --serial <EXACT_OPERATOR_CONFIRMED_SERIAL> \
  --stationary --parked --display-booted --cluster-normal --no-warnings \
  --head-unit-confirmed --adb-stable --no-other-adb-issuer \
  --operator-no-manual-adb --exclusive-adb-window
```

```text
CLARITYLINK R7E7I — EXPLICIT PHASE S READ-ONLY AUTHORIZATION

I authorize exactly one Phase S read-only inspection using repository
bmreyes25/ClarityLink PR #19 at HEAD [EXACT_REVIEWED_HEAD].
Collector SHA-256: 9bec4ecd58b49e50b1d27cc0807c14ee7407397cb078918c129d8783291c0464
Manifest SHA-256: bbd9afe14005ec6e3e68d6a5781232f538123aa04ce6a3932a697dd6789eb310
Clock-bound attestation SHA-256: [EXACT_REVIEWED_PRIVATE_ATTESTATION_SHA256]
Attestation expiry UTC: [EXACT_REVIEWED_EXPIRY]
Historical error bound: [EXACT_REVIEWED_SECONDS, AT LEAST 1800]
Current error bound: [EXACT_REVIEWED_SECONDS]
Clock-bound evidence and independent reviewer: [CONCRETE REFERENCES]

I freshly confirm the vehicle is stationary and safely parked; the center
display is fully booted; the instrument cluster is normal; no unexpected
warning indicators are present; the intended Honda head unit is connected;
the existing ADB connection is stable; no other terminal or app is issuing
Honda ADB commands; and I will issue no manual ADB commands during Phase S.
The exact intended ADB serial is [EXACT_OPERATOR_CONFIRMED_SERIAL].

I authorize only the frozen five-command sequence above, once, through the
unchanged collector. Require its zero-ADB dry-run first. All target commands
must use adb -s [EXACT_OPERATOR_CONFIRMED_SERIAL]. Timeout is 12 seconds per
command, retries and fallbacks are zero. Any mismatch, timeout, unexpected
response, or transport anomaly means stop and preserve private evidence.

I do not authorize process enumeration, ps, root, su, signals, kills,
diagnostic launch, file transfer, chmod, chown, deletion, Phase C, Test A,
Test B, ADB connection changes, or any other Honda command. The authorization
expires immediately after this one inspection. Stop all Honda operations and
report the classification and evidence path.
```
