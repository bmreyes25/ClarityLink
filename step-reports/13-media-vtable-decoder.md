# Step 13 — media vtable and decoder boundary

Date: 2026-09-28

## Scope

Offline-only examination of the exact ignored local `jmcs` ELF and its embedded DWARF. No vehicle, ADB, firmware, or implementation changes.

## Findings

DWARF identifies the linked generic sink as `mc_stream_sink` (`ops` at +0, `priv` at +4) with an interface table `mc_stream_sink_ifc`. Its +0x14 slot is explicitly named `process_data`; +0x10 is `alloc_buf`. `mc_stream_push_data` uses the +0x14 function pointer with `(sink, mc_stream_buf*)`. The buffer type carries `buf`, `buf_size`, `data_size`, `timestamp`, `free`, and `arg` fields.

The ELF separately includes an Android Stagefright/MediaCodec backend. `android_mediacodec_ctx_t` has source, surface context, width/height, codec, and input/output buffer fields. Its process function queues MediaCodec input. Surface setting stores the supplied surface context and calls codec initialization; configuration accepts a `SurfaceTextureClient` smart pointer. The static pass did not recover the concrete `mc_stream_sink_ifc` instance for the CarPlay stream, nor prove an edge from its `process_data` method to MediaCodec/H.264.

The listener port remains dynamic and is inserted into a setup dictionary; key meaning and outward advertisement are unresolved. Setup's +0x2b4 field and `_ScreenThread` context +0x1418 remain distinct unreconciled offsets.

## Decision

- Primary media path: partial.
- Generic interface dispatch: confirmed to `mc_stream_sink_ifc.process_data`.
- CarPlay H.264, decoder ownership/cardinality, and active Surface: unresolved.
- Display B implementation readiness: no.
- Runtime capture: not triggered by this pass; the next blocker is a static constructor/registration edge tying the active CarPlay sink table to a concrete method.

## Evidence files

See `research/carplay/media-object.md`, `media-vtable.md`, `carplay-decoder.md`, `decoder-surface-binding.md`, and `primary-object-ownership.md`.
