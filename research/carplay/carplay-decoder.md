# CarPlay decoder trace

The `jmcs` ELF contains an Android MediaCodec backend (`android_mediacodec_create`, `android_mediacodec_process_data`, codec initialize/start/stop/destroy routines, and H.264 media-info handling). Existing DWARF/disassembly notes describe its context and input/output buffer state.

There is still no proven edge from the active `CarPlay Screen` device registration or sink to this backend. Therefore:

| Item | Result |
|---|---|
| CarPlay concrete sink | Unknown |
| First video/H.264 function on CarPlay path | Unknown |
| H.264 reachable from active callback | Unknown |
| Decoder type for active CarPlay screen | Unknown; MediaCodec is present as a candidate backend |
| Decoder owner/storage | Unknown |
| Cardinality (global/per-device/per-sink/per-stream/session) | Unknown |
| Two decoders supported | Unknown |

Do not use backend existence as evidence of active-path reachability. Next resolve the registration match and follow its callback/object fields. See `decoder-surface-binding.md`, `media-ownership-graph.md`, and `mc-dev-attach.md`.
