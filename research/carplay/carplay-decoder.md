# CarPlay decoder and output trace

**Verdict: the CarPlay callback reaches a real generic media-stream handoff; its concrete vtable target and the actual output Surface remain unresolved.**

`mc_ScreenStreamProcessData` calls `mc_stream_alloc_buf` (`0x8e70c`) and `mc_stream_push_data` (`0x8ea18`). These functions dispatch to a linked media object through vtable slots `+0x10` (allocate buffer) and `+0x14` (push/process buffer). This establishes the handoff from the CarPlay callback into the media graph, but the linked object/table instance is not yet identified.

The `jmcs` ELF has a substantial Stagefright backend with named functions including `android_mediacodec_create`, `android_mediacodec_process_data`, `initialize_codec`, decoder-output, stop/destroy, and surface-setting helpers. It imports MediaCodec create/configure/start, input/output buffer operations, and output rendering. `initialize_codec` takes an `android_mediacodec_ctx_t` and `surface_ctx_t`; `configure` accepts a `SurfaceTextureClient` smart pointer. These establish a concrete backend implementation in this binary, but the callback's `+0x14` method has not been joined to those functions.

| Item | Result |
|---|---|
| Screen callback | `mc_ScreenStreamProcessData` (`0xbee91`) |
| Media handoff | `mc_stream_alloc_buf` -> linked vtable `+0x10`; `mc_stream_push_data` -> linked vtable `+0x14` |
| First confirmed H.264 boundary on this path | Not established beyond the linked vtable dispatch |
| Decoder implementation present | `android_mediacodec_create`, `android_mediacodec_process_data`, `initialize_codec`, output/stop/destroy functions |
| Decoder owner/cardinality | Backend uses `android_mmf_ctx_t` and `android_mediacodec_ctx_t`; CarPlay stream/session cardinality unknown |
| Codec and dimensions | Backend helpers exist; values for this screen stream unknown |
| Output target type | `surface_ctx_t` and `SurfaceTextureClient` configure argument |
| Actual CarPlay Surface/owner/binding | Unknown |
| Two decoder/output objects | Unknown |

The next static edge is the code that links the CarPlay stream to its media object and initializes that object's `+0x10/+0x14` method table. Until that is traced, H.264 and the decoder backend remain available native capability rather than proven consumer of this screen connection.

The generic ScreenStream context APIs and Honda per-stream context/counting remain confirmed; semantic screen/session identity is still unresolved.
