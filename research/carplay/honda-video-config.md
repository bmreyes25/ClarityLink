# Honda VideoConfig — Step 35

## Honda evidence

The exact Honda callback and media helper analysis does **not** identify a VideoConfig message value or prove that a named VideoConfig reaches `mc_ScreenStreamProcessData`. `mc_ScreenStreamProcessData` (`0xbee91`) parses callback-level length-prefixed records and transforms certain payloads, including adding four-byte start-code-like prefixes. The concrete linked sink is reached through `mc_stream_push_data`, but neither its concrete consumer nor codec-config handling is connected to this callback by current xrefs.

| Field | Honda finding |
|---|---|
| Message type/value | Unknown |
| Codec | H.264 is a strong lead from callback transformations and H.264/AVCC helpers elsewhere, but a specific Honda VideoConfig record is not proven |
| Width / height | Unknown |
| SPS / PPS | Extraction and ownership unknown |
| Profile / level / timescale / frame rate | Unknown |
| NAL length size / AVCC vs Annex B in wire payload | Unknown |
| Decoder extradata path | Unknown; concrete sink implementation not joined to callback |

## Prior-art comparison, not Honda facts

Pinned MU1440 MHI2 `STREAM111_PROTOCOL.md` treats VideoConfig's body as an AVC decoder configuration record (`avcC`) and extracts SPS, PPS, and NAL length size. Its receiver code parses avcC SPS/PPS, accepts optional opaque trailing data, creates Annex-B parameter-set bytes, and associates a codec generation. This supports a testable prior-art hypothesis, not a field map for Honda.

**Readiness:** `ClarityLinkVideoConfig` cannot yet have proven Honda fields; preserve future unknown config bytes as opaque until Honda discriminator and body boundary are established.
