# Step 43T1-PREP2 — offline runtime integration readiness

**Decision: `43T1_PREP2_COMPLETE`.** Start: `952907dfcb6376c046d4a7f9dbd5e18d8be8b788` (`main`, clean). End: PREP2 implementation commit (recorded below after commit; report-only metadata follows). This report covers only offline work. Honda contacted: **NO**. ADB used: **NO**. Target writes: **0**. No iPhone, CAN, USB injection, live Honda listener, vehicle session, Honda negotiation, deployment, binary modification, APK, startup, `/system`, `/data`, or block-device action occurred. The only socket test is host loopback.

## Workstream results

| Area | Result | Remaining Honda-only fact / limitation |
|---|---|---|
| CF static response map | `HONDA_CONFIRMED` construction and synchronous ownership map; internal CF-style symbols inventoried from hash-matched ELF | Post-Setup third-party mutation ABI, concurrency and project-created value ownership remain unexecuted/unproven |
| CF bridge | `CF_BRIDGE_OFFLINE_READY` clean-room model; borrowed inputs, temporary transaction ownership, copy-on-write, rollback and failure injection | No Honda `CFLite` execution or Honda Type111 schema acceptance |
| RAM attachment model | `RAM_ATTACHMENT_MODEL_READY` simulation with exact identity/context gates, compare-before-write, bounded lease and reverse cleanup | No real target memory permissions, attachment mechanism, RAM behavior or runtime permission |
| Independent verifier | `RESTORATION_VERIFIER_MODEL_READY`; separate immutable evidence input | No Honda process readback or reboot/post-reboot proof |
| Binding policy | Engine implemented; current decision `BIND_POLICY_PARTIAL` because placeholders are unset | Interface, address, family, and scope from future 43T0-D/D4 evidence |
| Wildcard policy | Prohibited for Honda; `0.0.0.0` and `::` rejected; host loopback only for tests | None; remains closed by design |
| Negotiation controller | Synthetic ordered controller and loopback end-to-end success/rollback scenarios; one connection, two-second accept window, 0.25-second first-byte window, 256-byte cap and five-second total event-time budget | Honda Type111 request, acceptance, reachability, runtime timing, and stock runtime invariants |
| Type110 preservation | Project model owns/closes no Type110, audio, or center-display state; tested as model invariants | Runtime confirmation during any later experiment |
| Type111 first-bytes oracle | `TYPE111_ORACLE_OFFLINE_READY`; bounded 256-byte structural classifier, no decryption or crypto fallback | Real Honda Type111 prefix/security evidence; no raw fixture is checked in |
| Type111 security | `UNKNOWN`; unknown/unsupported is fail-closed; no AES/ChaCha branch selected | Real Type111 prefix, framing, KDF, nonce/counter, and integrity behavior |

### Preserved CF static findings

The preserved binary hash is `cbc7ba881648fb8ffdfcc4c1100a028345c37134a2ae3b9dff7d76572851c232`. It is ELF32 ARM little-endian EABI5. The read-only symbol inventory confirms `CFGetTypeID`, array/dictionary/number/string type IDs, dictionary get/set/create, array create/append/count/index, number create/get, `CFRetain`, `CFRelease`, and `CFPropertyListCreateData`. `CFArrayCreateCopy` exists; a named mutable-copy wrapper for dictionaries or arrays was not found. The stock Setup path creates a mutable response dictionary, creates/appends the streams array through `_AddResponseStream`, serializes synchronously at the selected seam, and releases the response after the serializer. Honda's own Type110 ownership has its separate static ledger. Arbitrary project callout mutation and project-created child ownership remain unresolved.

### Ownership and rollback

The synthetic bridge allocates Type and port numbers, one stream dictionary and a newly allocated mutable array; array copy behavior uses the known CreateMutable/AppendValue pair. It holds the original array only for the synchronous transaction so serializer failure can attempt identity-guarded restoration. Precommit allocation failures leave the response unchanged. An injected rollback-set failure is surfaced and is not labeled restored. Fake-CF checks include ownership cleanup, use-after-release, double-release, failure injection, independent transactions and Type110 order/value preservation. These prove the test model only.

The attachment model compares the full known identity, architecture, callsite, target, continuation and fingerprints before a hypothetical write; detach compares the exact `CLAB` test token before restoration. It models no executable instruction bytes. Cleanup order and each failure seam are explicit. The separate verifier requires fresh exact bytes/context and absent listener/FD/worker/generation/bridge facts.

### Oracle and fixtures

Honda statically confirms a 128-byte Type110 header, LE32 body length, byte discriminator and observed opcode set. The oracle cap is 256 bytes, the declared-length threshold is a local guard only, and no crypto output exists. The sanitized 43P artifact records the PlayPort parser's modern ChaCha classification but contains redacted events rather than raw first bytes. Since shared 128-byte framing does not distinguish legacy AES from modern ChaCha, the oracle leaves a source-tagged PlayPort structural fixture `CLEAR_OR_UNKNOWN`. No raw prefix was reconstructed from redacted events.

## ECC review findings

Applied ECC security-review, coding-standards, Python-testing, and self-evaluation guidance. The review found no new vehicle deployment path; request/response objects are synchronous borrowed inputs; bridge mutation is copy-on-write and failure-injected; listener binding is evidence-gated and rejects wildcard; installer and verifier use separate state; unknown Type111 bytes never select crypto. A rollback failure remains an explicit failed state. No independent ECC reviewer service was available, so this is a manual ECC-guided review, not an independent external audit.

The fake CF runtime and end-to-end twin are explicitly synthetic and do not prove target behavior. The binding placeholders remain unresolved by design. No raw first-byte fixture is checked in; the oracle correctly leaves a source-tagged modern header unknown because it cannot distinguish crypto from the shared structural prefix. These are the intended Honda/runtime evidence boundaries, not unfinished offline implementation.

## Verification

- Focused PREP2 tests: **117 passed**, including CF bridge 26, attachment/detach 26, restoration verifier 13, binding policy 27, controller 6, oracle 17, and composed loopback integration 3 (some cross-cutting cases are counted in more than one category).
- Configured full offline suite (`tools/run_tests.sh`): **642 passed, 3 skipped**. Native host checks compiled and passed plain, ASan/UBSan, and TSan runs; self-locator smoke passed 3/3; all configured simulator JavaScript checks passed.
- Python compile/import validation and `git diff --check`: passed. Markdown relative-link validation: passed with no missing targets. Privacy/secret scan found no secret, MAC, private capture, or unredacted phone identifier in the new artifacts; wildcard strings are policy examples only. Historical capture-backed scripts remained skipped by the configured suite as intended.
- Commit/push/hosted Offline CI: pending.

## Decision and next step

`43T1_PREP2_COMPLETE`. No existing 43P redacted metadata was promoted into packet bytes. Remaining Honda-only unknowns are runtime CF ABI/ownership, target memory mechanism/permission and restoration/reboot evidence, 43T0-D/D4 network values, phone reachability and Type111 acceptance/framing/security. Runtime attachment and Type111 negotiation remain disabled and unauthorized.

```text
43T1 LIVE EXECUTION = NOT AUTHORIZED
TYPE111 HONDA NEGOTIATION = NOT AUTHORIZED
RAM ATTACHMENT ON HONDA = NOT AUTHORIZED
```

**The next vehicle milestone remains the read-only 43T0-D/D4 network observation. PREP2 does not authorize Honda RAM attachment, Type111 negotiation, or any modifying test.**
