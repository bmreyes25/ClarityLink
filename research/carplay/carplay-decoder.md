# CarPlay decoder and output trace

**Verdict: the generic screen stream dispatch is resolved to a named media-interface operation, but its concrete sink instance has not been connected to the Android decoder backend.**

`mc_ScreenStreamProcessData` (`0xbee90`) calls `mc_stream_alloc_buf` (`0x8e70c`) and `mc_stream_push_data` (`0x8ea18`). DWARF identifies the linked object as a `mc_stream_sink` interface: slot +0x10 is `alloc_buf`, and slot +0x14 is `process_data`. The CarPlay push call passes the linked sink and an `mc_stream_buf*`; the structure carries data pointer, size, timestamp, and buffer-free metadata.

The same ELF contains a concrete Stagefright/MediaCodec backend. `android_mediacodec_ctx_t` is 116 bytes and stores a base MMF context, source, surface context, width/height, codec and input/output buffer vectors. Its process routine calls MediaCodec input-buffer dequeue and queue operations. `android_mediacodec_set_surface(ctx, void*)` stores the supplied surface context and invokes codec initialization; that initialization configures MediaCodec with a `SurfaceTextureClient` smart pointer. These facts establish backend capabilities but not a call edge from the active CarPlay sink to that backend.

| Item | Result |
|---|---|
| Screen callback | `mc_ScreenStreamProcessData` (`0xbee90`) |
| Generic media object | `mc_stream_sink`, with `ops` and `priv` |
| +0x14 role | `mc_stream_sink_ifc.process_data` (DWARF-confirmed) |
| Concrete active target | unresolved |
| First H.264 boundary on CarPlay path | unresolved |
| Backend present | `android_mediacodec_create`, process/init/surface/start/stop/destroy helpers |
| Backend context | `android_mediacodec_ctx_t`; decoder cardinality on CarPlay path unknown |
| Output interface | `surface_ctx_t`; configure takes `SurfaceTextureClient` smart pointer |
| CarPlay output creator/host | unknown |

`mc_stream_link` semantics and direct PBS callers are now documented, but those generic pipeline construction functions are not proven to be the CarPlay screen builder. The missing join is the indirect device/factory registration that supplies the active sink. See `mc-stream-link.md`, `active-carplay-sink.md`, and `decoder-surface-binding.md`.
