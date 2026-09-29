# Honda screen-stream crypto — Step 34

**Scope:** offline structural analysis of the identity-verified `jmcs` ELF (SHA-256 `cbc7ba881648fb8ffdfcc4c1100a028345c37134a2ae3b9dff7d76572851c232`). No live key material is recorded.

## Type-110 derivation

Within `AirPlayReceiverSessionSetup` (`0x2854e0`), the inlined `_ScreenSetup` path reads `streams[i].streamConnectionID` as `uint64_t`, rejects zero, and calls `AirPlay_DeriveAESKeySHA512ForScreen` (`0x288d18`). The call arguments recovered in Step 33 are the receiver-session master-key buffer at `+0x1b8`, length 16, the stream connection ID, and output buffers for a 16-byte key and 16-byte IV. Honda installs the outputs through `AirPlayReceiverSessionScreen_SetSecurityInfo` (`0x287d28`) and clears temporary key/IV storage.

```text
authenticated receiver/session context
  master AES material (16 bytes) ─┐
  streamConnectionID (uint64) ────┴─> AirPlay_DeriveAESKeySHA512ForScreen
                                        -> per-screen key + IV
                                        -> screen security context
```

The receiver master key is session input; the ID distinguishes the screen stream's derived context. The stream `type` is used for dispatch but is not a parameter to the derivation function. No display UUID or separately named session ID is a proven direct input. This does not imply that a Type-111 stream is accepted by Honda: the current stock dispatcher rejects 111 before Type-110 screen setup.

## Security context and framing crypto

The derived key/IV are installed on the screen-session object passed to `AirPlayReceiverSessionScreen_SetSecurityInfo`. That routine initializes screen AES state; the receive path later decrypts video with `AES_CTR_Update` before `ScreenStreamProcessData`. Do not confuse `AES_CBCFrame_Init` (used by MHI2 as a narrow observation seam for session security setup) with Honda's screen-payload cipher. Honda Type-110 video uses AES-CTR in its recovered screen path.

The accepted fd is wrapped by `NetSocket_CreateWithNative` in `_ScreenThread` and owned by that wrapper during `ProcessFrames`; it is not proven stored in the screen object. Listener owner and thread context share a setup/session relationship, but the descriptor offset mapping is not fully reconciled.

## Type-111 assessment

| Question | Result |
|---|---|
| Type-110 derivation inputs | receiver master key (16 bytes) + `streamConnectionID` (`uint64`) |
| Stream type passed into derivation | No |
| UUID passed into derivation | Not observed |
| Separate session ID passed into derivation | Not observed; receiver session supplies master-key context |
| Honda Type-111 reuse proven | Unknown; Honda rejects 111 |
| Same derivation primitive appears reusable | Yes as a structural function contract, conditional on valid session key and ID |
| Live key bytes included here | No |

MHI2 source at pinned commit `c2f811f1a5c84dae3a62f4cf9b4a9e65fc3f7b3c` observes stock session security material at `AirPlayReceiverSessionSetSecurityInfo` / `AES_CBCFrame_Init`, then calls `AirPlay_DeriveAESKeySHA512ForScreen` with the Type-111 ID. This is prior-art evidence for an architecture, not Honda ABI or wire-schema evidence. See [MHI2 hook map](https://github.com/harman-f/mhi2_altscreen_carplay/blob/c2f811f1a5c84dae3a62f4cf9b4a9e65fc3f7b3c/docs/research/MU1440_GEN2_HOOK_MAP.md) and `research/carplay/prior-art-altscreen.md`.
