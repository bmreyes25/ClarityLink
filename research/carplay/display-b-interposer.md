# Display B interposer assessment

**Status: Display B implementation is not ready.**

The media callback path now has a typed generic boundary: `mc_stream_push_data` invokes `mc_stream_sink_ifc.process_data` at +0x14 with a sink and `mc_stream_buf*`. This is a useful candidate routing boundary, but the concrete sink instance used by the CarPlay screen and its `priv` ownership are not recovered. The Android MediaCodec backend and a replaceable surface-setting method exist, but neither is proven to be the active CarPlay consumer.

| Structural question | Finding |
|---|---|
| Two screen-session objects | UNKNOWN |
| Two TCP listeners | UNKNOWN; each observed setup asks for a dynamic port, which alone does not prove repeated setup |
| Two ScreenStreams | UNKNOWN end-to-end |
| Two media sinks | UNKNOWN |
| Two decoders | UNKNOWN |
| Two output Surfaces | UNKNOWN |
| Callback routing by generic stream/sink identity | Interface receives stream/sink objects, but display routing identity is UNKNOWN |
| Latent multi-screen support | PARTIAL generic structures only; no evidence of active multi-screen receiver support |
| Display B structurally possible | UNKNOWN |
| Ready for implementation | NO |

Hypothetical duplication points remain the screen-session setup/lifecycle and stream creation. A possible routing point is the generic sink `process_data` interface, contingent on proving the concrete sink and lifecycle. A possible output injection point is `android_mediacodec_set_surface(ctx, void*)`, contingent on proving that the CarPlay path reaches the backend and the supplied surface type is compatible.

Do not implement Display B from this evidence. The precise blocker is the missing constructor/registration edge that assigns the active CarPlay sink interface and binds it to a concrete media backend.
