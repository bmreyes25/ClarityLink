# AltScreen transport and presentation are separate planes

**Step 35 update, 2026-09-29.** Honda ELF is authoritative for Honda. MHI2 and xcertplay are implementation prior art.

## Transport / media security

```text
SETUP stream descriptor -> type dispatch -> streamConnectionID
 -> session master key + ID -> per-screen key/IV
 -> dedicated listener -> accepted NetSocket -> read/decrypt
 -> screen framing -> VideoConfig/H.264 -> media sink
```

Honda Type-110 confirms derivation inputs (16-byte session master material and uint64 ID), AES-CTR screen payload processing, dedicated listener and accepted `NetSocket`. It does **not** yet establish Honda's encrypted TCP frame header, message types, VideoConfig body, or access-unit boundaries. The downstream callback parses its own records and synthesizes four-byte start-code-like prefixes in some paths, but the final sink and decoder are unjoined.

## Presentation / UI ownership

```text
/info display descriptor and UUID -> phone display/UI selection
 -> future suggestUI/showUI/stopUI/ViewArea control -> presentation ownership
```

No direct UUID-to-stream crypto binding has been found. Honda PlatformControl/SessionControl symbols exist while exact command semantics remain unknown. MHI2 keeps transport and UI operations separate on its target; Honda ordering remains unknown.

## Consequence for Type 111

Do not require UUID-to-streamConnectionID mapping to model the media socket. A listener can bind a peer connection to its transport generation. However, the Type-111 negotiation contract and Honda wire framing/crypto compatibility remain blockers. MHI2's Type-111 implementation is evidence of feasibility on MU1440 only. Do not encode its 128-byte frame header as Honda fact.

**Step 35 gate:** transport/presentation split remains supported; Honda parser and independent crypto implementation are not ready. See `type111-transport-model.md` and the Step 35 report.
