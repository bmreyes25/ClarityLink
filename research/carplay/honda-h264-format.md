# Honda H.264 media format — Step 37

## avcC-to-record-width link

Honda `mc_ScreenStreamSetProperty` (`jmcs` `0xbe6fc`) passes type-1 CFData bytes to `H264ConvertAVCCtoAnnexBHeader` (`0x29f28c`). The helper derives `nalLengthSize = (avcC[4] & 3) + 1` and returns that integer through its output pointer. SetProperty stores the value in its callback context at `+0x14`. Honda `mc_ScreenStreamProcessData` (`0xbee90`, callback symbol `0xbee91`) reads that same context field at `+0x14` to choose the type-0 prefix parser. **The configuration-to-record-width linkage is proven.**

| Width at callback context `+0x14` | Prefix construction | Honda result |
|---:|---|---|
| 1 | one byte, unsigned length | explicit branch |
| 2 | `(p[0] << 8) | p[1]` | explicit big-endian branch |
| 3 | no parser branch | unsupported path; avcC helper can derive/store 3, but media callback does not consume it as a length width |
| 4 | `p[0]<<24 | p[1]<<16 | p[2]<<8 | p[3]` | explicit big-endian branch |

The low two avcC bits can derive widths 1 through 4. The callback implements 1, 2, and 4 only. A derived width of 3 is therefore a configuration/media incompatibility in this build. Zero or values above 4 cannot result from this helper's formula; other values at `+0x14` have no matching parse branch.

## Type-0 record loop and output

At callback entry, a separate byte at context `+0x11` selects a direct-copy path. When nonzero, Honda allocates a media buffer equal to the input body size, copies the body unchanged, copies the timestamp, and pushes it without reading the `+0x14` length selector or prepending stored SPS/PPS. When zero, it follows the length-record conversion path below. The code proves both modes; the value for the Type110 stream produced by the relevant Setup/config sequence is unresolved. The offline receiver exposes this as an explicit `direct_body_mode` input rather than guessing.

In its record-conversion path (`mc_ScreenStreamProcessData`, around `0xbf194`–`0xbf2fe`), Honda walks input records until the current cursor reaches the message body end. It reads the mode-selected prefix, computes each record end, emits `00 00 00 01`, and copies/transforms the record bytes. For mode 2 and 4, prefix bytes are assembled big-endian. It accumulates all records into one output allocation, then stores the produced byte count in `mc_stream_buf+8`, copies timestamp to `mc_stream_buf+16`, and calls `mc_stream_push_data` once (`0xbf2fe`) for that invocation. Therefore multiple length-prefixed records can be carried in one type-0 message and grouped into one media buffer.

The converter contains an additional byte-copy/zero-run normalization loop around `0xbf294`–`0xbf40e`; the four-byte start code is exact, but that loop's full transformation semantics are not sufficiently established to claim byte-for-byte equivalence to simple prefix removal for every H.264 payload. The offline extractor implements bounds-checked length-record removal and start-code insertion, while this normalization remains an explicit fidelity gap.

Honda performs cursor/end comparisons before record copies in the main path, but malformed-prefix corner cases include reads before all width bytes are proven available. ClarityLink's implementation checks every prefix and declared payload before slicing. Zero-length records produce a start code in the observed conversion loop; the offline extractor preserves that behavior. A 3-byte width reaches the callback's unsupported-mode path rather than a 3-byte endian parser.

## Config parameter-set policy and boundary

The type-1 avcC-like body is parsed by `H264ConvertAVCCtoAnnexBHeader`. Its SPS and PPS byte strings are retained as opaque records and each is prefixed with `00 00 00 01`. The converted config is stored at callback context `+0x08`, its byte count at `+0x0c`, and its NAL length width at `+0x14`. The `+0x10` flag is reset so the media callback prefixes the next produced type-0 output buffer with the stored parameter-set bytes, then sets the flag. There is no local NAL-type inspection of SPS/PPS in the config helper.

**Message-to-buffer boundary:** one type-0 ScreenStream message calls the callback once; the normal conversion path groups all records into one `mc_stream_buf` and makes one push. This is confirmed as a message-to-buffer boundary. Calling that buffer a complete H.264 access unit is high-confidence protocol/media interpretation, not explicit Honda nomenclature.

## Keyframe and decoder

No `nal[0] & 0x1f`, type-5 IDR flag, or sync-frame metadata assignment was found in this callback/config path. Keyframe detection is **absent in this layer**. `mc_stream_push_data` dispatches to `mc_stream_sink_ifc.process_data` at +0x14, but the active sink for the CarPlay stream remains unjoined. An Android MediaCodec backend exists; its `process_data` function queues one buffer and divides the stored timestamp by 1000 before `queueInputBuffer`, but no static registration edge proves it is the active CarPlay sink. Do not claim a concrete decoder or input-time unit for this stream.
