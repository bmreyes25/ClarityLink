# Honda VideoConfig — Step 36

## Honda branch and payload handoff

`AirPlayReceiverSessionScreen_ProcessFrames` dispatches header byte `+4 == 1` after reading the full header/body and, when enabled, decrypting the body. This branch loads header bytes `+16` and `+20` as binary32 floats, converts each to a CF double property, and—when the body length is nonzero—passes the body pointer and exact body length to `CFObjectSetPropertyData`. It does not call `ScreenStreamProcessData` in this branch and does not parse the config body in this function.

This is a **probable VideoConfig branch** because it performs stream-property updates and sends a distinct configuration-like data blob, matching the public screen-packet family. The CF property names and downstream consumer have not been resolved from this call path.

| Field | Honda result |
|---|---|
| Discriminator | 1 byte at header offset 4, value 1 enters this branch |
| Header values | float32 at offsets 16 and 20; each converted to a CF double property; semantic names unknown |
| Body | Body-size bytes at header offset 0; decrypted in-place first when session crypto is enabled; passed as CF data property without local parsing |
| Codec | H.264/AVC is probable by protocol family, not proven by Honda body inspection |
| avcC marker/SPS/PPS/NAL length size | Not parsed or validated by ProcessFrames; content format remains unknown |
| Profile / level / dimensions / FPS | Two floats are consumed, but meanings unknown; no SPS-derived values are recovered |
| Decoder extradata / SPS/PPS destination | Consumer of the property is not joined to this call path |

## Public/prior-art comparison

The [classic AirPlay screen packet reference](https://openairplay.github.io/airplay-spec/screen_mirroring/stream_packets.html) identifies type 1 as codec data and describes an `avcC` body. Pinned MHI2 MU1440 `STREAM111_PROTOCOL.md` likewise treats VideoConfig as avcC and extracts SPS/PPS and NAL length size. Honda's type-1 path matches the separate config branch but hands off opaque data; it does not prove avcC. `VIDEOCONFIG_FORMAT=UNKNOWN (avcC is a strong family hypothesis)`.
