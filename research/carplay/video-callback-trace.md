# Video callback and media helper trace

**Status: generic stream dispatch and framed-data callbacks confirmed; final codec/output edge still unresolved.**

`ScreenStreamProcessData` (`jmcs` `0x28e2c8`) loads a process-global callback and invokes it indirectly. It forwards the stream pointer and remaining process-data arguments. Honda's callback is `mc_ScreenStreamProcessData` (`0xbee90`, Thumb symbol `0xbee91`): `r0` is the callback's stream/context-like object, `r1` data, and `r2` length. It reads callback metadata/context fields, checks stream mode at `+0x14`, and walks framed records. Length-prefixed records are parsed in more than one width/byte order; the callback also writes four-byte start-code-style prefixes while transforming some record payloads.

## Helper `0x8e70c`

At call sites `0xbef86` and `0xbefe2`, arguments are: `r0` a callback object loaded from context-relative `+0x40`, `r1` length, `r2` output/length slot. The helper validates state, reaches context at `r0+0x0c`, calls `0x8d5f4`, then dispatches through a function pointer loaded from `[object+0x10]` with `(buffer, length, output-slot)` arguments. It returns that callback's result. This is a framed-buffer/custom callback dispatch helper, not itself a proven decoder. `mc_ScreenStreamProcessData` also calls `0x8ea18` on two downstream branches.

The start-code-like prefix and the presence elsewhere in this ELF of H.264/AVCC helper names support a **high-confidence H.264 framing lead**, but the exact first confirmed CarPlay H.264 function/decoder invocation is still not proven by a cross-reference from this callback. The H.264 helper strings and Android MediaCodec imports cannot by themselves be joined to this callback path.

| Callback property | Finding |
|---|---|
| Stream/data/length args | stream/context-like pointer `r0`, data pointer `r1`, length `r2` |
| Per-stream context | generic `ScreenStreamSetContext` / `ScreenStreamGetContext` APIs exist; actual identity semantics unresolved |
| Record parsing | structured framing and length handling in callback |
| Helper `0x8e70c` | custom framed-buffer callback dispatch via indirect operation at object `+0x10` |
| Other downstream helper | `0x8ea18`, called twice by the callback |
| First confirmed H.264 boundary | not yet established at this exact callback's data flow |
| Decoder and output | not connected to this callback by current xref evidence |
