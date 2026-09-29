# Honda Type-110 screen framing — Step 35

This note distinguishes TCP reads, encrypted screen transport, downstream `mc_ScreenStreamProcessData` records, and prior-art framing. Honda evidence is authoritative for Honda; MU1440 protocol details are not silently transferred to this target.

## Proven Honda receive chain

```text
_ScreenThread
 -> SocketAccept -> accepted fd -> NetSocket_CreateWithNative
 -> AirPlayReceiverSessionScreen_ProcessFrames
 -> ReadInternal/recv into screen-session buffer (+0x48), up to 128 bytes
 -> screen AES-CTR update (screen security state initialized by SetSecurityInfo)
 -> ScreenStreamProcessData
 -> registered callback mc_ScreenStreamProcessData (0xbee91)
 -> callback parses its own length-prefixed record forms and transforms some payloads
 -> mc_stream_alloc_buf (0x8e70c) -> mc_stream_push_data (0x8ea18)
 -> linked sink process_data interface at +0x14
```

The TCP request size is not a packet/header size. The callback receives `(stream/context-like pointer, data pointer, length)` in `r0/r1/r2`. Its `+0x14` state selects among parsing branches; the code reads length-prefixed records using more than one width/byte order and writes four-byte start-code-like prefixes while transforming some records. This is downstream evidence, not the encrypted TCP envelope grammar.

## Honda TCP/frame boundary fields

| Offset | Size | Endian | Meaning | Evidence |
|---|---:|---|---|---|
| — | — | — | Honda TCP screen header / opcode / payload length / sequence / timestamp / flags | Unknown in current exact-binary analysis |
| — | — | — | Honda transport message discriminator (including VideoConfig) | Unknown |
| — | — | — | Whether one plaintext frame spans multiple reads or one read contains multiple frames | Unknown |
| — | — | — | Length/padding/alignment rule at encrypted socket layer | Unknown |

## Comparison only: pinned MU1440 MHI2 implementation

Pinned MHI2 `docs/research/STREAM111_PROTOCOL.md` describes a **128-byte ScreenStream header**, little-endian 32-bit body size at offset 0, opcode at offset 4, and opcode-specific body; it identifies VideoConfig and VideoFrame classes. This is MU1440/AirPlay 210.81-era evidence. It is not a recovered Honda header, even though Honda's initial read also asks for up to 128 bytes.

## Decision

`FRAME_BOUNDARY_RULE(Honda)=UNKNOWN`. The downstream parser is partially understood, but no justified ClarityLink parser can yet turn Honda ciphertext/plaintext socket data into reliable `VideoConfig` or H.264 objects. A parser hard-coding MHI2's 128-byte header would be a prior-art profile, not a Honda-compatible implementation.

**References:** `research/carplay/accepted-fd-dataflow.md`, `research/carplay/video-callback-trace.md`, `research/carplay/media-object.md`, `research/carplay/screen-tcp-framing.md`, pinned MHI2 `docs/research/STREAM111_PROTOCOL.md`.
