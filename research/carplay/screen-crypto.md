# Honda screen crypto

The Step 36 byte-level call contract and CTR state analysis supersedes the earlier partial Step 34 note. See [`honda-screen-crypto.md`](honda-screen-crypto.md) for Honda's exact in-place body-only AES-CTR arguments, continuous counter state, context initialization/finalization, and current model readiness.

The Step 34 derivation inputs remain in force: 16-byte receiver session master material plus nonzero uint64 `streamConnectionID` produce 16-byte key and IV outputs via `AirPlay_DeriveAESKeySHA512ForScreen`. No real key/IV material is recorded. Honda Type-111 compatibility remains unproven because stock dispatch rejects Type 111 before screen setup.
