# Step 43Q-A — offline legacy dual-screen crypto/session twin

**Status: IMPLEMENTED AND LOCALLY VERIFIED.** Offline synthetic model only. Honda Type111 crypto remains `HONDA_UNKNOWN`.

## Scope and base

- Starting commit: `4efcf017817ab35315c7aa28a8afbacc5042a434` (`main`), clean working tree.
- This milestone reuses the existing Type110 screen KDF, CTR model, ScreenStream parser, and receiver core. It adds no network listener, runtime attachment, vehicle access, `jmcs` patch, APK, configuration change, or deployment.
- Parent session material and stream IDs in tests are deterministic synthetic values. No captured media or real session/key/IV material is used.

## Architecture

`LegacyDualScreenTwin` owns immutable parent material and role-keyed `LegacyScreenSession` objects. `TYPE110` and `TYPE111_SYNTHETIC` are explicit roles. Each screen constructs its own derived key/IV, `ScreenCryptoModel`, `HondaScreenReceiverCore`, parser, configuration, and buffered input state. The synthetic secondary calls the validated existing `derive_honda_type110_screen_key_iv` primitive with its own ID; this is a model of the external-prior-art hypothesis, not a Honda Type111 API claim.

A duplicate live ID is rejected before adding a screen with `DuplicateStreamConnectionID` (`code=duplicate_stream_connection_id`, role pair supplied, no IDs/secrets in the message). Destroying a screen is role-scoped and idempotent. Crypto teardown invalidates the context and clears its mutable counter/keystream/key fields; Python immutable byte objects are not a secure-memory-erasure guarantee. A new secondary requires a distinct currently unused ID and creates a new object while retaining the original Type110 object.

A parser, crypto, config, or media extraction exception closes only the screen whose `feed` failed, and reports the fixed sanitized error `synthetic screen input rejected`. Type111 behavior remains synthetic and external-prior-art-backed.

## Deterministic evidence and verification

The new focused module has 14 test cases covering:

- Type110-only baseline and explicit role identity;
- distinct synthetic IDs and separately instantiated derived key/IV, crypto, parser, and receiver objects;
- A-only and B-only advancement, plus interleaved runs compared with independent per-screen controls;
- reset, destroy, and recreate B while A remains active with byte-for-byte equal CTR state;
- malformed oversized B input with A parser buffer/config/CTR unchanged, then valid A completion matching the control path;
- typed duplicate-ID rejection without partially adding B, plus invalid uint64 rejection;
- mutable-state separation across independent parent sessions;
- sanitized errors and representations;
- destroy invalidation of B's retained crypto reference.

The AES block callable in these tests is a deterministic XOR fixture expressly documented as a CTR state-mechanics test double, not AES. Existing fixed Type110 SHA-512 KDF regression vectors remain in `tests/negotiation/test_setup_contract.py`; existing continuous CTR regression coverage remains in `tests/transport/test_screen_parser.py`.

Verification: focused crypto/KDF/parser set **63 passed** (including 14 new twin test cases); configured full offline suite **315 passed, 4 skipped**; self-locator smoke **3 passed**; simulator JavaScript checks all passed; `git diff --check` passed. The first full-suite invocation used the system Python without pytest and stopped at the runner's dependency preflight; rerunning with the repository's `.venv` passed. No hosted CI run has been observed yet.

## ECC review

Applied ECC security-review, coding-standards, and Python-testing guidance. Manual review checked for mutable cross-screen aliases, shared CTR objects, parser state coupling, exception-path sibling mutation, duplicate-ID ambiguity, teardown ownership, real-key fixtures, secret-bearing repr/error paths, and evidence overclaiming. The only crypto function default is the pre-existing Type110 KDF; comments and evidence docs explicitly qualify its use for Type111 as a hypothesis. No dedicated independent ECC reviewer endpoint was available in this workflow, so this is a manual ECC-guided review, not an independent audit.

## Evidence classification

- Existing Type110 KDF inputs and AES-CTR ScreenStream behavior: `HONDA_CONFIRMED` (existing evidence, not newly established here).
- Per-screen legacy Type111 derivation: `EXTERNAL_PRIOR_ART` / `HYPOTHESIS`; not Honda-confirmed.
- Isolation, malformed-input containment, duplicate rejection, reset, destroy, and recreate behavior in this twin: `LAB_SYNTHETIC_CONFIRMED` by deterministic tests.
- 43P topology and PlayPort parser labels remain `CURRENT_IOS_LAB_CONFIRMED` for that lab profile only. `MODERN_CHACHA_SCREEN` is not used to derive or validate this legacy model.
- Honda Type111 security mode, KDF success, proposed response acceptance, listener/session ABI, and Type111-only teardown/restart remain `HONDA_UNKNOWN`.

## Limitations and next milestone

This proves only that ClarityLink's offline model can instantiate two independent legacy-style screen states from synthetic inputs using the existing Type110 primitive. It does not prove Honda Type111 uses AES, accepts this derivation or setup, or has the modeled lifecycle. Generation numbering, restart policy, sockets/listeners, and runtime lifecycle integration are deliberately not implemented.

Recommended next action: **43Q-B — offline synthetic Type111 generation, teardown, and restart lifecycle twin.** Do not begin 43Q-B as part of this report.
