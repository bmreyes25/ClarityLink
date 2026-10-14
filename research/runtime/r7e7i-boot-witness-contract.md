# R7E7I boot-witness contract, version 1

## Claim boundary

The contract can support only this claim: **the specific original invocation, independently established as preceding observation A, could not still be a process after a genuine later kernel boot observed at B**. It cannot establish that no later invocation ran, that the old file disappeared, that no relaunch mechanism exists, that the current process set is clear, or that cleanup/Test A is safe.

The mechanism is conditional and presently unavailable for vehicle planning: preserved Honda evidence identifies Linux `3.1.10+`, and upstream v3.1 source has no `boot_id` interface. Exact Honda source/config is unavailable, so a vendor backport is unproven. Android UI, zygote, init, or infotainment service restarts that leave the kernel running do not satisfy the boot-change criterion.

## Required observations and evidence

Before any observation is proposed, offline evidence must show the exact Honda kernel image/source contains a `boot_id` implementation with per-kernel-execution stability and that the applicable sysctl is enabled. Generic modern Linux documentation cannot substitute for this exact-build proof. Each later observation includes: schema and label; exact ADB serial; separately sourced hardware identifier; Android build fingerprint and kernel release; raw canonical boot UUID; capture command/result and exit status; collector/manifest SHA-256; sequence; and a receipt over the full canonical record. The independent reviewer verifies source, exact target mapping, key provenance and receipt bytes. A digest detects byte changes only; it does not identify a signer.

The pair must use the same target identity at A and B. A serial alone is insufficient if it could map to another head unit; any identity ambiguity blocks. `boot_id` must parse as a canonical non-nil UUIDv4. The precise Honda kernel must be shown to expose a per-kernel-boot UUID stable during a boot. No timestamps from the original Test A host, Git commit metadata, or unauthenticated device clock may be used to establish the old event's timing.

Sequence proof requires the independent reviewer to authenticate that A was captured before B, and to bind B to A's receipt/hash. Independently signed sequential receipts or an independently witnessed append-only sequence may serve; a host-written integer, adjacent filenames, local mtime, or an unverified claim does not. Separately, the original Test A invocation must be established before A through its hash-bound preserved command/result receipt and reviewed causal/operator evidence. If this cannot be established without a historical time assumption, reject the route.

The implementation requires four receipt hashes: `baseline`, `later`, `ordering`, and `invocation_relation`, plus a canonical receipt-manifest hash. Real signatures, evidence custody, hardware identity, exact kernel capability and reviewer identity remain outside the pure host model and must be checked independently. Schema fields claiming `INDEPENDENT_REVIEW_PASSED` are assertions, never cryptographic proof. Current status: the source tree does not support claiming Honda boot-ID availability.

## Fail-closed cases

Reject missing baseline/later observation; malformed, nil, same or unavailable boot ID; different serial/hardware/build; unverified target mapping; sequence conflict; missing or changed receipt; invalid signature/key provenance; historical-time ordering; original invocation not proven before A; ambiguous observation source; synthetic evidence represented as real; exact kernel capability unknown; review missing; or a userspace-only restart. A same ID means this pair did not prove a later kernel boot. It does not prove no reboot happened and rebooted back into the same improbable value; the model never treats UUID collision resistance as absolute.

## Independent outcomes after a valid pair

- Historical invocation: eligible for independent finding `HISTORICAL_INVOCATION_TERMINATED` only after review of all evidence gates.
- Current references: separately `CURRENT_REFERENCES_UNKNOWN`, `CURRENT_REFERENCES_PRESENT`, or `CURRENT_REFERENCES_ABSENT_WITH_COMPLETE_VISIBILITY` using the existing bounded procfs evidence contract. Empty `ps` is not evidence of complete visibility. PID/start-time identity, executable `/proc/PID/exe`, maps, descriptors, zombies/reaping and permission coverage remain relevant.
- Relaunch: independently classify `NO_PROJECT_PERSISTENCE_EVIDENCED`, `PROJECT_PERSISTENCE_FOUND`, `UNRESOLVED_EXTERNAL_RELAUNCH_PATH`, or `RELAUNCH_AUDIT_INCOMPLETE`. The first label is scoped to audited project actions and is not a universal no-actor guarantee.
- File: verify exact current device/inode, type, mode, owner, size and content digest separately. Boot ID does not establish path presence/absence or file identity.
- Phase C: only `PHASE_C_READY_FOR_SEPARATE_REVIEW` after all evidence and safety gates; it remains `PHASE_C_NOT_AUTHORIZED` absent a new single-use authorization.
- Test A: remains `TEST_A_BLOCKED` until recovery, cleanup decision, artifact and timeout prerequisites are independently resolved and a new authorization is given.

## Model and fixtures

`tools/r7e7i_boot_witness.py` parses JSON and evaluates the closed fields offline. Its result is always model-only or review-required. It cannot contact ADB, validate detached signatures or create authorization. `tests/tools/test_r7e7i_boot_witness.py` uses only explicit synthetic values. Fixture hashes and reviewer flags are never vehicle evidence. Historical times are rejected as support for the boot route.

## Freshness and expiry

There is no reusable approval or attestation. Capability documentation can be reused only for the exact same kernel image/build and is invalidated by a kernel/build change or contrary observation. Observation receipts are immutable records but have no standing authorization. Any future cleanup review must use fresh current-reference, relaunch, exact-file, target and operator safety evidence collected for that separate authorization. Any hardware/build identity change, receipt/key revocation, unexplained launch, restart between an observation and a dependent current-state inspection, or authorization expiry invalidates the dependent decision.
