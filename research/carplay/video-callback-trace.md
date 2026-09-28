# Video callback and media helper trace

**Status: generic stream dispatch and framed-data callbacks confirmed; final codec/output edge still unresolved.**

`ScreenStreamProcessData` (`jmcs` `0x28e2c8`) loads a process-global callback and invokes it indirectly. It forwards the stream pointer and remaining process-data arguments. Honda's callback is `mc_ScreenStreamProcessData` (`0xbee90`, Thumb symbol `0xbee91`): `r0` is the callback's stream/context-like object, `r1` data, and `r2` length. It reads callback metadata/context fields, checks stream mode at `+0x14`, and walks framed records. Length-prefixed records are parsed in more than one width/byte order; the callback also writes four-byte start-code-style prefixes while transforming some record payloads.

## Helpers `0x8e70c` and `0x8ea18`

The symbol table resolves `0x8e70c` as `mc_stream_alloc_buf` (Thumb entry `0x8e70d`). At call sites `0xbef86` and `0xbefe2`, arguments are `r0` a stream object loaded from callback context-relative `+0x40`, `r1` requested size, `r2` output-buffer slot. It obtains the linked object at stream `+0x0c`, checks link state through `mc_stream_is_linked` (`0x8d5f4`), then loads a method from the linked object's vtable at offset `+0x10` and calls it as `(linked-object, size, output-slot)`. This is buffer allocation, not decoding.

`0x8ea18` resolves as `mc_stream_push_data` (Thumb entry `0x8ea19`). It follows the linked-object relationship and dispatches through vtable slot `+0x14` with the linked object and media buffer. These are the real media-pipeline extension points reached from the CarPlay callback. The concrete vtable instance and writes/initializer selecting its allocator and process-data targets are unresolved.

The start-code-like prefix and the presence elsewhere in this ELF of H.264/AVCC helper names support a **high-confidence H.264 framing lead**, but the exact first confirmed CarPlay H.264 function/decoder invocation is still not proven by a cross-reference from this callback. The H.264 helper strings and Android MediaCodec imports cannot by themselves be joined to this callback path.

The missing edge is the `mc_stream_link`/media-framework construction path that supplies the concrete linked object and its method table. The data function at vtable `+0x14` has not been joined to the H.264 pipeline.

| Callback property | Finding |
|---|---|
| Stream/data/length args | stream/context-like pointer `r0`, data pointer `r1`, length `r2` |
| Per-stream context | generic `ScreenStreamSetContext` / `ScreenStreamGetContext` APIs exist; actual identity semantics unresolved |
| Record parsing | structured framing and length handling in callback |
| Helper `0x8e70c` | `mc_stream_alloc_buf`; linked-object vtable dispatch at `+0x10` |
| Helper `0x8ea18` | `mc_stream_push_data`; linked-object vtable dispatch at `+0x14` |
| First confirmed H.264 boundary | not yet established at this exact callback's data flow |
| Decoder and output | not connected to this callback by current xref evidence |
