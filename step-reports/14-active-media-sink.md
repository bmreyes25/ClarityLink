# Step 14 — active CarPlay media sink trace

Date: 2026-09-28

## Scope

Offline static analysis of the local `jmcs` ELF and DWARF. No vehicle, ADB, firmware changes, Display B implementation, or packet fabrication.

## Findings

`mc_stream_link` at `0x8da00` takes `src` and `sink` and returns `result_t`. It verifies link state, stores reciprocal references at `src+0x0c` and `sink+0x08`, invokes each endpoint's `init_instance` method at operations offset +0x08, and proceeds with linked setup/message handling. The sink type debug record is an 8-byte prefix (`ops`, `priv`); the link field at +8 lies beyond that prefix and indicates the handle is embedded in or points to a larger endpoint representation.

All direct callers found are in `mediacore/service/pbs/mc_pbs.c`: `add_sink_stream_pair` (`0x4c318`), `create_pipeline` (`0x4c8cc`), and `create_pipeline_nommf` (`0x4d5fc`). The pair helper receives a sink pointer and obtains a media-framework source from a stream; the pipeline builders construct/link generic pipelines. The inspected CarPlay source callbacks include `mc_carplay_screen_stream_init_instance` and `mc_ScreenStreamStart` (which attaches a device through `mc_dev_attach`), but the device manager dispatch is indirect and the active sink factory/ops table is not statically joined to those functions in this trace.

The existing MediaCodec backend remains a separate available implementation. No concrete `mc_stream_sink_ifc` table for the active CarPlay screen was resolved; consequently its `process_data` target, `priv` type, H.264 reachability, decoder ownership/cardinality, and active Surface remain unknown.

## Decision

- Active CarPlay sink: unresolved.
- `mc_stream_link` generic construction semantics: confirmed.
- CarPlay-to-MediaCodec edge: unresolved.
- Display B readiness: no.
- Static analysis has not established absence of a backend; the precise gap is the indirect device/factory registration that supplies the sink to the CarPlay stream.

See `research/carplay/mc-stream-link.md`, `active-carplay-sink.md`, and `media-ownership-graph.md`.
