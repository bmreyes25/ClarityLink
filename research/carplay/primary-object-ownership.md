# Primary screen object ownership (static evidence)

```text
ReceiverSession
  +-- screen setup and listener creation [confirmed]
  +-- _ScreenThread listener field +0x1418 [confirmed at thread-context base]
       +-- accepted native FD -> NetSocket wrapper [confirmed]
       +-- ScreenStream / Honda process callback [confirmed]
            +-- generic stream source and linked sink [interface/layout confirmed]
                 +-- mc_stream_sink_ifc.process_data (+0x14) [confirmed role]
                      +-- concrete active sink object [unknown]
                           +-- MediaCodec backend [present, not connected]
                                +-- SurfaceTextureClient configure support [present, not connected]
```

`mc_stream_sink` layout is `ops` +0, `priv` +4. The generic source and buffer layouts are documented in `media-object.md`. The current trace does not establish that the sink is uniquely owned by a CarPlay ScreenStream, that the Android backend is that sink, or that its `priv` leads to the decoder context. Setup's output FD field +0x2b4 and the thread-context listener field +0x1418 remain unreconciled: no same-base proof was found in this pass.

This graph is an evidence graph, not a proposed implementation design.
