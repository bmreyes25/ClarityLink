# Media ownership graph

```text
Receiver/ScreenSession
  └─ ScreenStream callback path [CONFIRMED]
      └─ mc_stream source endpoint [HIGH CONFIDENCE from callback + DWARF]
          └─ mc_stream_link relationship [generic link behavior CONFIRMED;
             active CarPlay link creation UNKNOWN]
              └─ mc_stream_sink
                  ├─ ops -> mc_stream_sink_ifc [type/layout CONFIRMED]
                  │   ├─ alloc_buf +0x10 [role CONFIRMED]
                  │   └─ process_data +0x14 [role CONFIRMED;
                  │      active CarPlay target UNKNOWN]
                  └─ priv [active type/owner UNKNOWN]
                      ├─ MediaCodec decoder [UNKNOWN connection]
                      └─ output Surface [UNKNOWN connection]
```

`mc_stream_link(src, sink)` stores reciprocal link pointers at `src+0x0c` and `sink+0x08` (the latter is beyond the 8-byte sink interface prefix), then invokes endpoint initialization operations. The direct call chain found is PBS pipeline construction (`create_pipeline` / `add_sink_stream_pair`), but no edge proves it builds the CarPlay screen path. A separate MediaCodec backend and surface setter are present in the binary without a proven join to the active sink. See `mc-stream-link.md`, `active-carplay-sink.md`, and `decoder-surface-binding.md`.
