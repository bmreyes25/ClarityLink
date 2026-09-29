# Honda Type-110 screen crypto — Step 35

**Binary:** exact local Honda `jmcs`, SHA-256 `cbc7ba881648fb8ffdfcc4c1100a028345c37134a2ae3b9dff7d76572851c232`. No key/IV bytes are recorded.

## Derivation and installation

`AirPlayReceiverSessionSetup`'s Type-110 path (`0x2854e0`) reads nonzero `streamConnectionID` (`uint64`) and calls `AirPlay_DeriveAESKeySHA512ForScreen` (`0x288d18`) with the receiver-session 16-byte master-key material and the ID, producing 16-byte screen key and IV outputs. It installs them via `AirPlayReceiverSessionScreen_SetSecurityInfo` (`0x287d28`). The setter initializes screen AES state at screen object +0xc8 through helper `0x28d9b4`; prior AES state is finalized through `0x28daec`.

```text
session master material (16 bytes) + streamConnectionID (uint64)
 -> AirPlay_DeriveAESKeySHA512ForScreen
 -> screen key + initial IV (16 bytes each)
 -> AirPlayReceiverSessionScreen_SetSecurityInfo
 -> AES state initialization
 -> ProcessFrames decrypts video body with AES_CTR_Update
 -> ScreenStreamProcessData
```

Type and display UUID are not direct inputs to the recovered derivation call. Honda Type 111 is rejected by its stock dispatcher; Honda Type-111 reuse remains unproven.

## Cipher model and reset behavior

Honda's screen payload cipher is **AES-CTR**, not AES-CBC. `AES_CBCFrame_Init` is a distinct session-security observation seam used by MHI2 prior art; it is not the Honda screen payload decrypt call. The AES-CTR state is initialized when screen security is installed, updated in `AirPlayReceiverSessionScreen_ProcessFrames`, and finalized when that screen session stops. This supports a persistent per-screen-stream CTR context across update calls.

The inspected evidence does not establish that the IV is reset per message, that a frame counter is mixed into the IV, or the precise update boundaries for VideoConfig versus VideoFrame. CTR does not impose CBC-style PKCS padding, but no padding interpretation should be added to the receiver parser without evidence. Whether any framing layer separately constrains ciphertext lengths is unknown. Do not implement crypto from the word “CTR” alone: exact AES context layout/API behavior and Honda plaintext frame boundary are still missing from this repository's analysis.

## Readiness

- Key derivation inputs: sufficiently recovered for an offline contract; no real key material included.
- Cipher mode: AES-CTR, high confidence from exact-target call-chain evidence.
- IV progression/reset semantics at individual message boundaries: unknown beyond session-context initialization/update/final lifecycle.
- Standalone offline crypto implementation: **not ready** until the exact update arguments and reset semantics are captured from Honda call-site analysis and synthetic vectors can be grounded without vehicle secrets.

**References:** `research/carplay/accepted-fd-dataflow.md`, Step 34/35 `ProcessFrames` and `SetSecurityInfo` disassembly, `research/carplay/prior-art-altscreen.md`, pinned MHI2 `docs/research/STREAM111_PROTOCOL.md` (comparison only).
