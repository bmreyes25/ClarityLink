# Active CarPlay sink status

## Verified abstract dispatch

The Honda screen callback reaches `mc_stream_alloc_buf` and `mc_stream_push_data`. DWARF types the objects as generic `mc_stream_src`/`mc_stream_sink` graph endpoints and `mc_stream_buf`. Sink interface slot +0x14 is named `process_data`; the invocation receives sink and buffer.

## Construction trace

`mc_stream_link(src, sink)` stores reciprocal relationship pointers and calls endpoint `init_instance` operations. Its direct callers in this ELF are `add_sink_stream_pair`, `create_pipeline`, and `create_pipeline_nommf`, all from the generic `mediacore/service/pbs/mc_pbs.c` subsystem. `add_sink_stream_pair` obtains an MMF source from a stream and receives the sink as an argument. The PBS path does not, in available call-edge evidence, connect to the active CarPlay screen setup or Honda screen callback.

The Android MediaCodec backend is created through its own media adapter/backend path (including `android_stream_set_media_info` call edges). No active CarPlay sink table, constructor, or `priv` object was found that joins `mc_stream_push_data` to that backend. Do not infer that the generic PBS sink argument is the CarPlay sink.

| Question | Finding |
|---|---|
| Active CarPlay sink type | Unknown |
| Ops table address | Unknown |
| `process_data` target | Unknown for active CarPlay stream |
| `priv` type/owner | Unknown |
| CarPlay-to-MediaCodec link | Unresolved |
| H.264 path from this dispatch | Unknown |
| Active decoder cardinality | Unknown |
| Active output Surface/owner | Unknown |
| Stream-to-sink display identity | Unknown |

The specific remaining static gap is the operation/factory path that supplies the sink pointer linked to the CarPlay screen source. `mc_stream_link` is a generic linker and does not select that sink.
