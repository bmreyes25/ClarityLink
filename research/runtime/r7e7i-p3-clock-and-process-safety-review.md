# R7E7I P3-C1–C3 evidence review

## Scope and decision

Offline host-only review of the preserved R7E7I evidence, clock-attestation gate,
Phase S package identity, and current-process safety criteria. No ADB command,
Honda contact, target write, target execution, process sweep, signal, or deletion
was performed. All tests use clearly synthetic host fixtures.

**Decision: `PHASE_S_BLOCKED`.** No production clock attestation was created.
The current host-clock uncertainty is not bounded by the evidence available in
this review. Therefore the boot-time inequality cannot be evaluated with
defensible inputs, and there is no Phase S authorization proposal.

## P3-C1: clock-error method

### Historical event uncertainty

The private failure record is mode `0600` and hashes to
`21e6551fde4498603dbfc9129aa4f32a61b0f0c7e89f3a70ba5035cfccee430e`. Its
recorded finish is `2026-10-12T02:14:44.929697Z`; it records diagnostic start
and process state `UNCERTAIN`. This is the event whose latest possible time
must be bounded, not the later Phase R file observation.

GitHub Actions run `38196454003` reports creation at `2026-10-12T02:36:36Z`,
head `243ee18fbfa5dd53b64c1c414dade12740a415c8`, and successful completion.
The API metadata response carried HTTP `Date: Tue, 13 Oct 2026 00:53:29 GMT`.
The review report says that run's review describes the already-failed event.
That chronology can support an upper bound only after an independent reviewer
checks the actual run/review payload and its server-clock margin. The 1,311.07
second gap between the recorded failure finish and run creation is not itself a
clock-error bound. The old manifest's 1,800 second minimum remains conditional,
not an established fact.

### Current host-clock uncertainty

The host reported `2026-10-13T00:54:09Z`; the single GitHub response above
reported `00:53:29Z`. They were not simultaneous bracketed samples, and no
independent source accuracy limit or NTP measurement artifact was preserved.
Agreement at that granularity does not bound offset, drift, or step. No current
error number is supportable from these observations.

### Independent chronology and monotonic interpretation

The chronology source must be independent of the host under review and must
have a documented maximum clock error. Preserve the source response/run record,
request bracket, source identity, retrieval method, and SHA-256; a URL or a
reviewer's assertion alone is insufficient. Host monotonic time can measure
elapsed duration between local samples and reveal an in-window wall-clock step.
It cannot establish UTC offset. Target `/proc/uptime` measures elapsed time
since kernel boot (including suspend), not wall time. The target's two-decimal
format is rounded conservatively by adding `0.01` seconds to the observed
uptime when deriving the earliest possible boot time.

For failure finish `F`, historical error budget `H`, host inspection start UTC
`T`, current host error budget `C`, and observed uptime `U`:

```
latest_prior = F + H
earliest_boot = T - C - (U + 0.01 seconds)
termination is established only if earliest_boot - latest_prior > 1 second
```

Equality, overlap, missing bounds, invalid boot identity, or an in-window clock
step fails closed. This proves only that the old invocation ended before the
observed boot; it says nothing about later relaunch or current mappings.

### Schema, expiry, binding, provenance

`r7e7i-clock-attestation.schema.json` defines separate historical and current
bounds, source claims, exact frozen-artifact bindings, explicit monotonic and
inequality semantics, a named reviewer and provenance reference, and issue /
expiry times. Expiry is capped at 24 hours. The host-only validator requires a
mode-0600 attestation, checks exact evidence/collector/validator/manifest hashes, verifies
a detached GPG signature using an explicitly supplied trusted keyring, checks
that the actual signing fingerprint equals the independently supplied expected
fingerprint and the named reviewer fingerprint, and rejects weak or stale
bounds. It hashes and checks sibling mode-0600 chronology and clock-calibration
receipt files. It does not create the signed file or decide whether the reviewer is
trustworthy; the keyring and expected fingerprint must come through a separate
trusted channel. No such reviewer key or valid source receipts were provided,
so no signed attestation exists.

## P3-C2: Phase S package verification

The preserved Phase R review evidence is mode `0600`, SHA-256
`001e13ba7c5911a5d03e10114d6d8925cb3e3fa4c619b2ce2ba396bd1cae3ddd`. It records
the exact path, size/mode/owner, remote MD5 and package SHA-256, with
`process_safety_established: false`. The current manifest freezes source hash,
both evidence hashes, command list, 12-second per-command timeout, and zero
retries, fallbacks, writes, launches, or cleanup. The command sequence remains
`adb version`; `adb devices`; exact-serial boot ID; `/proc/uptime`; same boot ID.
Procfs grammar, exact sole-device gate, command order, stop-on-first-fault,
timeout behavior, and private mode-0600 evidence are covered by the fake-ADB
matrix. These tests establish host control-flow behavior only.

The previous invocation termination result and current process absence remain
distinct. Even a successful later-boot inequality cannot authorize pathname
removal or establish no current executable reference. Since this new signed
attestation gate has no real attestation/keyring, the package is not READY for
separate Phase S authorization. Do not run Phase S.

## P3-C3: current-process safety tree

1. If the exact pathname is absent, record only `NO_PATHNAME_TO_REMOVE`; current
   mappings and relaunch safety remain unresolved.
2. If present, first bind the exact regular file identity (device/inode where
   available, size, mode, owner, and cryptographic hash). Any ambiguity blocks.
3. Require separate evidence that the old invocation terminated. A process
   name, empty `ps`, current boot alone, or a stale PID is insufficient.
4. To establish no current reference would require complete visibility of
   process executable links, mappings and open descriptors for the exact file
   identity. PID reuse requires start-time identity and revalidation around
   reads; zombies have terminated but retain a PID until reaped. Permission-
   limited `/proc` makes a negative result inconclusive. A pathname unlink also
   does not revoke already-open file references.
5. Separately audit relaunch mechanisms. A clean process observation is only a
   point-in-time fact and cannot exclude a later service, init, user, or other
   relaunch.
6. Only complete, race-bounded negative reference evidence plus a reviewed
   no-relaunch basis could qualify for a distinct safety review. Any unknown or
   conflict blocks.

No process-sweep package is proposed: the original PIDs are unavailable, the
preserved reports do not establish procfs visibility or a no-relaunch basis,
and a broad `/proc` enumeration is explicitly outside this scope. No narrow
read-only command presently identified can resolve all these questions. Phase
C/path removal remains blocked. The pure decision model is explanatory and
performs no inspection.

## Verification record

- Focused clock-edge, fake-ADB, and process-safety matrices: **54 passed**.
- Configured repository checks (`tools/run_tests.sh`): **1,282 passed, 14
  skipped**, 3 self-locator smoke checks, all simulator JavaScript checks, and
  whitespace validation passed.
- ECC security/code review followed the ECC review checklist. The signed
  attestation is fail-closed on trust-root mismatch, evidence/package hash or
  source-receipt changes, timestamp format/expiry, bound arithmetic, and
  incomplete process visibility. A direct-script import issue found during
  review was fixed and the dry-run path rechecked.
- Test fixtures are marked synthetic and are not candidate production evidence.
