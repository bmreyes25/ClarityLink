# Honda ScreenStream and media-core input — Step 36

## Calls and branch inputs

| Site | Branch | Arguments / bytes | Result |
|---|---|---|---|
| `AirPlayReceiverSessionScreen_ProcessFrames` `0x2880a2` | header byte `+4 == 0` | stream `[screen_session+0x1ec]`; decrypted body pointer; LE32 body length; converted header time; trailing zero fields | Calls generic `ScreenStreamProcessData` |
| ProcessFrames config path `0x288120` | header byte `+4 == 1` | two header float32 values at +16/+20 become CF doubles; decrypted body bytes and length become CF data property | Separate property/config delivery; not ScreenStreamProcessData |
| `ScreenStreamProcessData` callback dispatch | registered Honda callback | generic stream/data/length/timing arguments forwarded indirectly | Invokes `mc_ScreenStreamProcessData` (`0xbee91`) |
| `mc_ScreenStreamProcessData` `0xbf2fe` | length-record conversion branch | writes transformed data-size to `mc_stream_buf+8`; copies callback timestamp to `mc_stream_buf+16`; invokes `mc_stream_push_data` | Pushes constructed buffer to linked sink interface `process_data` (+0x14) |

## Step 37 config linkage and payload bytes

Opcode 1 reaches `mc_ScreenStreamSetProperty` (`0xbe6fc`), which calls `H264ConvertAVCCtoAnnexBHeader` (`0x29f28c`). The helper converts the avcC-like SPS/PPS arrays into start-code-prefixed bytes and returns the NAL prefix width. SetProperty stores converted config pointer/size at callback context `+0x08/+0x0c`, NAL width at `+0x14`, and resets one-time prepend flag `+0x10`. The type-0 media callback uses the same selector and prefixes its next output media buffer with that converted config. It then walks all length records and calls `mc_stream_push_data` once for the assembled buffer.

The +0x14 selector linkage is direct. Supported callback modes are 1-byte, 2-byte BE, and 4-byte BE. Formula-derived width 3 has no callback branch. The byte-copy loop also has zero-run handling at `0xbf294`–`0xbf40e`, whose complete media significance remains unresolved; therefore the exact Annex-B boundary bytes are proven but the offline extractor's copy operation does not yet claim bit-exact equivalence for all payload patterns.

`mc_ScreenStreamProcessData` also tests callback context byte `+0x11` before its length-record path. If nonzero, it copies the complete input body unchanged into one media buffer, preserves the timestamp, and pushes it; it bypasses length parsing and the pending config-prefix path. The Type110 path's effective value for this flag is not established, so `HondaScreenReceiverCore` exposes `direct_body_mode` as an explicit input instead of selecting a value from assumption.

## Media buffer bytes and metadata

The callback's conversion loop writes `00 00 00 01` before parsed length-delimited record data in the Annex-B conversion branch. The configured parameter-set bytes are prepended once after each new config. The final output size is computed as produced output pointer minus buffer base and stored at `mc_stream_buf.data_size` (+8). Callback time is copied into `mc_stream_buf.timestamp` (+16). The linked object receives this constructed media buffer through `mc_stream_push_data`.

`mc_stream_buf` is a generic media buffer, not an opaque 128-byte screen packet. The type-0 callback performs record transformation before push. Type-1 config bytes are handled outside the callback as a CF data property. Honda's exact H.264 AU semantics, SPS/PPS relation, keyframe flag, sink implementation, and concrete decoder call are not proven. Thus media-core byte contents are **known in transformation shape but not fully classified as complete access units**.

References: exact Honda callback disassembly `0xbee90..0xbf2fe`, `research/carplay/media-object.md`, and `research/carplay/video-callback-trace.md`.
