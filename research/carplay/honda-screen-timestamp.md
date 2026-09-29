# Honda ScreenStream timestamp trace — Step 37

## Proven path

- Header bytes `+0x08..+0x0f` are loaded as a little-endian 64-bit integer by `AirPlayReceiverSessionScreen_ProcessFrames` (`0x287d8d`).
- When the per-session conversion flag is set, Honda calls the configured function pointer at screen-session `+0x20`, with context at `+0x18` and the loaded 64-bit value. The converted 64-bit result is retained for the message.
- Without the converter flag, it uses `UpTicks()` instead of the wire value.
- Opcode 0 passes the resulting 64-bit value to `ScreenStreamProcessData`; the media callback copies it into `mc_stream_buf.timestamp` at offset `+0x10`.
- The generic Android MediaCodec backend contains code that divides a media-buffer timestamp by 1000 before `MediaCodec::queueInputBuffer`. The active CarPlay sink is not statically linked to this backend, so that conversion does not establish the active stream's timestamp unit.

## Unknowns

The header field is **NTP-like by prior-art position only**. Honda's dynamic converter implementation/provider and the field's exact fixed-point/timebase interpretation have not been identified. There is no Honda-confirmed 2^-32 fraction conversion, seconds/fraction split, or absolute/relative epoch mapping in the recovered call chain. The two type-1 float32 fields are separate config properties and do not resolve timestamp semantics.

ClarityLink keeps this value as `timestamp_raw` in the offline receiver events. It must not label the raw integer NTP or convert it into milliseconds/microseconds until the converter contract is recovered.
