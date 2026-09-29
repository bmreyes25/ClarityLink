# Honda screen crypto — Step 36

Exact offline target: Honda `jmcs`, SHA-256 `cbc7ba881648fb8ffdfcc4c1100a028345c37134a2ae3b9dff7d76572851c232`.

## Key context and update call

Type-110 setup passes the 16-byte receiver-session master-key material and nonzero uint64 `streamConnectionID` to `AirPlay_DeriveAESKeySHA512ForScreen`, producing a 16-byte screen key and 16-byte IV. `AirPlayReceiverSessionScreen_SetSecurityInfo` calls `AES_CTR_Init` on context at screen object +0xc8; replacing a prior context calls `AES_CTR_Final`.

The screen payload call at `AirPlayReceiverSessionScreen_ProcessFrames` `0x288080` is:

| Argument | Value | Meaning |
|---|---|---|
| arg0 | `screen_session + 0xc8` | persistent AES-CTR context |
| arg1 | body allocation pointer | input ciphertext |
| arg2 | LE32 payload/body length loaded from header offset 0 | byte count |
| arg3 | same body allocation pointer | output plaintext; in-place |

It runs only when security-enabled byte `screen_session+0x1e4` is set, after the header and complete body have been read and after header timestamp processing, but before opcode dispatch. Therefore **header encrypted: NO; body encrypted: YES when screen security is active**. For type 0, plaintext body reaches `ScreenStreamProcessData`; for type 1 it reaches the config data-property path. No header bytes enter AES_CTR_Update.

## AES_CTR implementation and state

`AES_CTR_Init` (`0x28d9b4`) calls `AES_set_encrypt_key(key, 128, ctx)`, copies 16 IV bytes to context +0xf4, zeroes the stream-byte position at +0x114, and clears state flag +0x118. `AES_CTR_Update` (`0x28d9dc`) accepts arbitrary byte length, XORs source with generated AES counter-block bytes, writes output, retains partial-block position +0x114 between calls, and advances the 16-byte counter when a block is consumed. The counter increment propagates from context byte +0x103 back toward +0xf4, so the last/high-address byte of the copied IV is the least significant counter byte (big-endian 128-bit counter arithmetic). The active init sets the context mode flag to zero, so it stores the updated offset after calls.

**CTR_STATE_MODEL: continuous over encrypted body bytes on one screen session.** Context is not reinitialized per 128-byte header, message, or video frame. Headers consume no CTR bytes; every protected body's bytes advance the same state in sequence. Context resets when new screen security is installed and is finalized on screen-session cleanup. Stream-type input is not part of the observed derivation call; Honda Type-111 compatibility remains unproven.

No padding is added or removed by the CTR implementation. This does not define any future ClarityLink Setup/key-derivation ABI. No real/session key or IV is stored in this note.

**Offline status:** The byte-level AES_Decrypt operation contract and counter continuity are now recovered. An offline CTR state model with injected key/IV and AES block primitive is justified. This repository implements only the state model; its tests use a deterministic toy block function and do not validate AES output against a known-answer vector. Honda's SHA512 screen-key derivation input serialization remains a separate proof requirement before implementing that derivation.
