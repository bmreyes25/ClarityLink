# ClarityLink Type-111 transport model — Step 35

**Status:** architecture candidate only; no live hooks or receiver implementation.

## Proposed plane split

```text
SETUP Type 111 descriptor (exact Honda schema unknown)
 -> preserve/copy descriptor and streamConnectionID
 -> use established receiver-session security context to derive per-screen key/IV
 -> create ClarityLink-owned listener and return peer-compatible dataPort response
 -> accept socket bound to that transport generation
 -> decrypt with AES-CTR if Honda Type-110-compatible crypto is proven
 -> parse Honda screen framing (currently unknown)
 -> emit VideoConfig and H.264 access units only after the wire grammar is established

/info display descriptor / UUID and UI ownership remain a separate presentation plane.
```

Honda confirms Type-110 uses session master material plus `streamConnectionID` for screen derivation, listener allocation and accepted-socket processing. Honda stock dispatch rejects Type 111. Pinned MHI2 source reuses the stock derivation primitive and a separate AES-CTR receiver for Type 111 on its MU1440 target, and treats UI control separately. This makes reuse plausible, not Honda-proven.

## Prior-art framing comparison

MHI2's pinned `STREAM111_PROTOCOL.md` specifies its own 128-byte ScreenStream header, body-size/opcode fields, `avcC` config and AVCC VideoFrame payload. Honda's TCP header/body grammar, VideoConfig value, and exact access-unit rules remain unknown. Therefore the proposed `parse same screen framing` transition is explicitly conditional; no ClarityLink Honda listener can yet claim media-compatible receipt.

## Abstraction boundary candidate

- `ClarityLinkScreenTransport`: socket lifetime and ordered encrypted bytes.
- `ClarityLinkScreenCrypto`: session-derived screen key plus streaming AES-CTR state; no embedded real keys.
- `ClarityLinkScreenFrameParser`: only after Honda header/length/opcode are established.
- `ClarityLinkVideoConfig` and `ClarityLinkH264AccessUnit`: typed outputs only after config and access-unit boundaries are proven; unknown config data stays opaque.

The cleanest current boundary is **after Honda screen framing and decryption**, before codec/media delivery. Honda's media sink may be bypassable by a ClarityLink-owned Type-111 endpoint, but Honda acceptance, Setup delegation, response identity fields, crypto compatibility, and socket framing are not proven.

## First future transport experiment (not executed)

Offline prerequisites first: recover byte-level Honda Type-110 framing and validate parser + crypto against synthetic inputs. A later, separately authorized controlled test should score levels independently: (1) phone connects to Type-111 listener; (2) decryption succeeds; (3) a valid Honda screen header parses; (4) VideoConfig parses; (5) an H.264 access unit is extracted. No decoder/rendering is required for level 5. Current readiness is **NO** because levels 2–5 lack a Honda wire oracle.
