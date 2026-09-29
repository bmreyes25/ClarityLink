# Honda H.264 wire format and media path — Step 36

## From ScreenStream message to callback

For message type 0, ProcessFrames sends the decrypted body as one call to `ScreenStreamProcessData` (callsite `0x2880a2`) with stream object `[screen_session+0x1ec]`, body pointer, body length, converted presentation time, and zeroed trailing metadata. The generic wrapper dispatches via the registered callback table to Honda `mc_ScreenStreamProcessData` (`0xbee91`). Message type 1 takes a separate CF-property path and does not go through this callback in ProcessFrames.

`mc_ScreenStreamProcessData` walks length-delimited items using the selected per-stream parser mode at callback context `+0x14`:

| Mode value | Input length prefix observed |
|---:|---|
| 1 | one-byte length |
| 2 | two-byte big-endian length |
| 4 | four-byte big-endian length |

The parser walks/validates records and in its conversion loop writes the exact four bytes `00 00 00 01` before output record data. It allocates a media buffer sized from the transformed output, sets `mc_stream_buf.data_size` to the produced-byte count, copies the callback timestamp to `mc_stream_buf.timestamp` at +16, then calls `mc_stream_push_data` (`0x8ea18`). This proves downstream Annex-B start-code synthesis for this record-conversion path; the exact NAL classes and whether all stream modes use the same transformed path are not established.

## What remains unknown

- The body is length-delimited per the per-stream parser mode, but Honda's intended mode for this stream generation is not statically tied to the actual callback context.
- The four-byte prefix is an Annex-B start code. The following bytes are parsed length-delimited record bytes, but it is not proven from this path whether one record is one NAL, a complete AU, or another wrapped unit.
- No proof that the callback extracts SPS/PPS or detects NAL type 5 as keyframe.
- No Honda avcC parser is connected to the type-1 config body.
- The concrete `mc_stream_sink_ifc.process_data` implementation and decoder remain unidentified.

**HONDA_VIDEO_WIRE_FORMAT:** length-prefixed callback records using mode-selected 1/2/4-byte big-endian lengths, followed by downstream Annex-B prefix synthesis in the converter branch. Calling the incoming type-0 body “AVCC” is premature; 4-byte mode is structurally similar, but stream-mode ownership and AU semantics remain unresolved.

**KEYFRAME:** unknown for Honda. Public classic AirPlay docs do not establish Honda's implementation.
