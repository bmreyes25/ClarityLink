# Honda ScreenStream and media-core input — Step 36

## Calls and branch inputs

| Site | Branch | Arguments / bytes | Result |
|---|---|---|---|
| `AirPlayReceiverSessionScreen_ProcessFrames` `0x2880a2` | header byte `+4 == 0` | stream `[screen_session+0x1ec]`; decrypted body pointer; LE32 body length; converted header time; trailing zero fields | Calls generic `ScreenStreamProcessData` |
| ProcessFrames config path `0x288120` | header byte `+4 == 1` | two header float32 values at +16/+20 become CF doubles; decrypted body bytes and length become CF data property | Separate property/config delivery; not ScreenStreamProcessData |
| `ScreenStreamProcessData` callback dispatch | registered Honda callback | generic stream/data/length/timing arguments forwarded indirectly | Invokes `mc_ScreenStreamProcessData` (`0xbee91`) |
| `mc_ScreenStreamProcessData` `0xbf2fe` | length-record conversion branch | writes transformed data-size to `mc_stream_buf+8`; copies callback timestamp to `mc_stream_buf+16`; invokes `mc_stream_push_data` | Pushes constructed buffer to linked sink interface `process_data` (+0x14) |

## Media buffer bytes and metadata

The callback's conversion loop writes `00 00 00 01` before parsed length-delimited record data in the Annex-B conversion branch. The final output size is computed as produced output pointer minus buffer base and stored at `mc_stream_buf.data_size` (+8). Callback time is copied into `mc_stream_buf.timestamp` (+16). The linked object receives this constructed media buffer through `mc_stream_push_data`.

`mc_stream_buf` is a generic media buffer, not an opaque 128-byte screen packet. The type-0 callback performs record transformation before push. Type-1 config bytes are handled outside the callback as a CF data property. Honda's exact H.264 AU semantics, SPS/PPS relation, keyframe flag, sink implementation, and concrete decoder call are not proven. Thus media-core byte contents are **known in transformation shape but not fully classified as complete access units**.

References: exact Honda callback disassembly `0xbee90..0xbf2fe`, `research/carplay/media-object.md`, and `research/carplay/video-callback-trace.md`.
