# CarPlay decoder trace

The `jmcs` ELF contains an Android MediaCodec backend (`android_mediacodec_create`, `android_mediacodec_process_data`, codec initialize/start/stop/destroy routines, and H.264 media-info handling). The registration scan is callback-ranked and its exact `CarPlay Screen` winner and attach callback remain unidentified.

| Item | Result |
|---|---|
| CarPlay concrete sink | Unknown |
| First video/H.264 function on active CarPlay path | Unknown |
| H.264 reachable from active callback | Unknown |
| Decoder type on active path | Unknown; MediaCodec is present as a candidate backend |
| Decoder owner/storage | Unknown |
| Cardinality (global/per-device/per-sink/per-stream/session) | Unknown |
| Two decoders supported | Unknown |

Backend existence does not establish active-path reachability. Continue by proving the `CarPlay Screen` comparator result and attach callback, then trace the returned device object to its sink. See [decoder-surface-binding.md](decoder-surface-binding.md) and [media-ownership-graph.md](media-ownership-graph.md).

## Step 17 status — winner remains unresolved (2026-09-28)

The offline pass confirms generic registration and ranking only. `dev_attach` selects the strictly highest unsigned slot `+0` result (initial best 0; ties retain the earlier node), then dispatches slot `+4`. The concrete list entry/interface/context installed for `"CarPlay Screen"` is not statically recoverable from the local `jmcs` artifact. Therefore this note does not assign an active backend, sink, decoder, or Surface. See [device-match-semantics.md](device-match-semantics.md) and [Step 17](../../step-reports/17-carplay-registration-winner.md). The exact blocker is runtime registration state (or its producer), not absent `jmcs`/DWARF. Display-B readiness remains **No**.
