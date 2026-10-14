# CL-IMP-07 — Secondary transport and security boundaries

**Status:** offline security-provider hardening implemented. Production Type111 security remains fail closed. No Honda or live-iPhone session was accessed.

## Implemented

- Security context generations and stream connection IDs are validated as positive unsigned 64-bit integers; Python booleans are rejected as integers.
- The explicit offline ChaCha fixture accepts only a 32-byte immutable key input and non-empty provenance, and accepts only byte inputs with a 128-byte header and a protected body between the 16-byte tag minimum and the existing 8 MiB Type111 frame ceiling.
- A closed fixture context cannot be reopened after its key buffer is zeroed. Invalid tags do not advance the nonce counter, as already covered by the receiver tests.
- Receiver setup refuses to reuse one security-provider object for Type110 and Type111 and preserves the active primary context when rejecting such an alias.
- `EvidenceRequiredSecurity` remains the default encrypted Type111 path without an explicitly injected lab provider. No MFi path, credential retrieval, or inferred Honda cryptography was added.

## Validation and limits

Focused provider/receiver tests cover malformed values, over-limit data, invalid context fences, one-shot cleanup, replay behavior, and primary/secondary object-alias rejection. These host tests validate defensive behavior only. They do not prove that the lab ChaCha profile is Apple's Type111 cipher, that an authorized Type111 key can be derived, or that Honda/iPhone session delegation exists. Independent ECC review and the full offline regression suite are required before milestone commit.
