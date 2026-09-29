# Honda H.264 wire format and access units — Step 35

## Honda evidence

`mc_ScreenStreamProcessData` walks callback-level length-prefixed records (with multiple branch-dependent length widths/byte orders) and emits four-byte start-code-like prefixes during at least some payload transformations. That is evidence of H.264 Annex-B conversion work in the callback, but it does not prove the socket's incoming payload is AVCC, prove which records are H.264 access units, or establish an access-unit completeness boundary. The callback reaches `mc_stream_alloc_buf` and `mc_stream_push_data`; the final sink and decoder/configuration calls remain unresolved.

| Property | Honda result |
|---|---|
| Ciphertext body decrypt mode | AES-CTR (screen path) |
| Incoming media format | Unknown; AVCC/length-prefixed is a lead, not established for this Honda callback |
| NAL length field width / endianness | Unknown at Honda socket/media boundary |
| Annex-B prefixes | Four-byte prefix synthesis is observed in downstream callback branches; exact applicability/data flow is partial |
| Keyframe signaling | Unknown; no proven Honda transport flag or NAL inspection branch identified |
| Frame timestamp/duration/index | Unknown at TCP boundary; generic `mc_stream_buf.timestamp` exists, but this callback does not prove how it is sourced |
| Complete access-unit boundary | Unknown |
| Concrete MediaCodec consumer | Not connected by current xrefs |

## Prior-art comparison

Pinned MU1440 MHI2 documents decrypted VideoFrame bodies as AVCC length-prefixed H.264, uses the NAL-length-size from avcC, identifies IDR by NAL type 5, and converts NALs to Annex-B for its local consumer. Those are MHI2 implementation details and cannot be used to fill Honda's unknowns.

**PROCESS_DATA_INPUT:** generic stream/context-like object, pointer to callback data, byte length. After callback parsing, `mc_stream_push_data` passes a constructed media buffer to linked sink `process_data`; the concrete buffer bytes, size, and timestamp are record-branch-specific and final sink remains unknown. `mc_stream_buf` layout includes `data_size` at +8 and `timestamp` at +16.
