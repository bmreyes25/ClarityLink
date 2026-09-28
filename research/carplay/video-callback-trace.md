# Video callback trace

**Status: generic data dispatch and Honda callback parser confirmed; decoder/output consumer unknown.**

The generic `ScreenStreamProcessData` wrapper (`jmcs`, VA `0x28e2c9`) dispatches its stream pointer and process-data arguments through a global function pointer. The Honda callback `mc_ScreenStreamProcessData` (`jmcs`, VA `0xbee91`) receives the stream argument in `r0`, data pointer in `r1`, and length in `r2` (visible entry moves to `r8`, `r4`, `r7`). It examines fields in the callback context, supports several packet/record cases, and calls helper `0x8e70c` while processing data. The excerpts do not identify that helper as a decoder or show decoded frames or an Android output object.

| Callback property | Finding |
|---|---|
| Generic registration | One Honda callback table is installed in the singleton `libcarplay_proxy.so` storage; six lifecycle/data callbacks |
| Generic callback args | Stream object plus data/timing/metadata arguments; stream context is available through stream offset `+8` APIs |
| Honda process-data args | Stream/context-like pointer, data pointer, length; exact payload semantic mapping remains partial |
| Data classification | Structured/tagged record processing; H.264 frame receiver is not conclusively identified |
| Callback routing by stream | Generic callback receives stream pointer: structurally yes at the generic ABI. Honda's existing callback-table registration remains singleton, and a screen identity key is unproven |
| Callback routing by context | Context pointer exists per stream; semantic identity/routing ability unknown |
| Decoder call | Not established |
| Output surface | Not established |

There is no evidence yet for `Stream A -> Decoder A` and `Stream B -> Decoder B` in Honda's implementation. A generic stream/context dispatch architecture could in principle route instances, but that is an architectural possibility, not demonstrated behavior or protocol support.

The precise missing artifact is a focused disassembly/xref trace from `mc_ScreenStreamProcessData` and its helper `0x8e70c` into the receiver's decoder initialization, decode submission, and output-target setup, including the owning library/object.
