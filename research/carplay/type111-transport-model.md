# ClarityLink Type-111 transport model — Step 36

**Status:** offline envelope and CTR state models are implemented; executable Type-111 receiver remains not ready.

## Transport candidate

```text
SETUP descriptor (Honda Type-111 schema remains unknown)
 -> keep streamConnectionID and established session master material
 -> derive per-screen key/IV
 -> separate listener/accepted transport generation
 -> read plaintext 128-byte header
 -> LE32 body length; byte opcode at offset 4; exact body read
 -> AES-CTR decrypt body in-place with per-stream continuous state
 -> type 0 -> timestamped ScreenStream media callback / ClarityLink H.264 extractor
 -> type 1 -> VideoConfig/config-property path
 -> other message handling per proven switch
```

Honda Type-110 now confirms fixed 128-byte header, body length at offset 0, low message byte at offset 4, timestamp-like data at +8, and body-only AES-CTR. Type 111 is still rejected by Honda stock dispatch, so same behavior on Honda Type-111 is not directly proven.

## Compatibility findings

- **Header family compatibility:** YES as a reusable *family parser*: Honda Type-110 agrees with the classic 128-byte/LE32 length/early discriminator layout; pinned MHI2 Type-111 uses that same legacy ScreenStream family. Honda's own Type-111 negotiation is not tested or accepted by stock code.
- **VideoConfig compatibility:** UNKNOWN for a Honda Type-111. Honda Type-110 type 1 is config-like and matches public avcC prior art, but Honda does not parse or validate avcC in this path.
- **H.264 compatibility:** UNKNOWN at the access-unit/keyframe level. The Honda callback's mode-specific length records and Annex-B conversion are partly recovered, but type-1-to-decoder and complete-AU semantics are unresolved.
- **Crypto compatibility:** UNKNOWN for Honda Type-111. Honda Type-110's AES-CTR update state and derivation inputs are recovered; MHI2 demonstrates using the stock screen derivation plus CTR for Type 111 on its target. Honda's type 111 is rejected before this path.

## Implemented offline boundary

`src/claritylink-transport/screen_parser.py` parses the fixed Honda header and body-size framing incrementally, preserving unknown header bytes and raw wire body. The body remains ciphertext when security is active. The local max-body setting is an allocation-safety policy, not a protocol maximum. `crypto_model.py` models the proven continuous CTR counter/partial-block state using an injected AES block encryptor; it embeds no session keys and includes no derivation function.

The parser and CTR-state model do not claim to parse avcC, emit complete H.264 access units, implement Setup/listeners, or provide a real AES backend. A self-contained Type-111 receiver therefore remains **NO**.
