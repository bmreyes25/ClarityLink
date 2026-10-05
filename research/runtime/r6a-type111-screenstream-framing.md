# R6A Type111 ScreenStream framing

`LegacyHondaType110Profile` is the bounded 128-byte, little-endian-length parser supported by [stock Honda Type110](../carplay/honda-screen-framing.md). `LegacyType111PriorArtProfile` fails explicitly. `CurrentIOSType111Profile` implements the [PlayPort ScreenStream](https://github.com/shilapi/xcertplay/blob/master/shared/src/main/java/com/shilapi/xcertplay/airplay/ScreenStream.kt) prior-art 128-byte header, little-endian length, opcode 0/1 and bounded 8 MiB body; it passes the exact header to the security provider as authenticated data. 43P used PlayPort, but a raw current-iOS vector has not been retained. The R5Z generated-clear path still calls the Type110-family parser as a declared synthetic experiment; no automatic profile detection is allowed.

| Field | Current evidence | Type111 status |
|---|---|---|
| connection preamble | 43P socket connected | bytes unknown |
| 128-byte header, length, opcode, timestamp | Honda Type110 static and PlayPort current-iOS parser | Host prior-art profile implemented; raw Type111 capture absent |
| encryption boundary, tag, nonce | 43P modern classification and PlayPort source | host prior-art profile: 16-byte tag, header AAD, per-stream counter; real vector absent |
| VideoConfig | 43P event observed and PlayPort source | clear opcode-1 avcC extraction implemented; real vector absent |
| AVCC vs Annex-B, NAL boundaries | PlayPort source converts length-prefixed access units | strict host AVCC converter; actual iPhone codec still unobserved here |
| keyframe/recovery | public prior art | current iOS unknown |

A strict AVCC access-unit converter and SPS/PPS `avcC` extractor sit behind the host decoder boundary. Generated encrypted H264 reaches FFmpeg; real iPhone media has not reached this receiver.
