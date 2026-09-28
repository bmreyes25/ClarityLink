# Display B interposer assessment

**Status: Display B implementation is not ready.**

The screen callback reaches a typed generic sink contract: `mc_stream_sink_ifc.process_data` (+0x14), called with a sink and `mc_stream_buf*`. `mc_stream_link(src, sink)` stores a reciprocal link and invokes endpoint initialization. Its direct callers are generic PBS pipeline helpers/builders; no direct CarPlay caller or resolved indirect factory edge identifies the active CarPlay sink.

The binary contains a MediaCodec backend and replaceable surface setter, but neither is proven to be the sink reached by the active screen stream. No decoder cardinality or active Surface ownership claim can be made.

| Structural question | Finding |
|---|---|
| Two screen-session objects | UNKNOWN |
| Two TCP listeners | UNKNOWN; dynamic bind does not prove repeated setup |
| Two ScreenStreams | UNKNOWN end-to-end |
| Two concrete media sinks | UNKNOWN |
| Two decoder instances | UNKNOWN for CarPlay |
| Two active output Surfaces | UNKNOWN |
| Context routes streams to separate displays | UNKNOWN |
| Display B structurally possible | UNKNOWN |
| Ready for implementation | NO |

Potential duplication remains screen-session and stream creation. The sink selection point is in the unresolved device/factory path; surface injection could use the backend setter only if that backend is proven to serve this stream and the Surface type is compatible.

**Precise blocker:** the indirect device/factory registration supplying the concrete sink to the CarPlay stream is not resolved.
