# Decoder and output path trace

**Verdict: partial native stream path; concrete decoder/surface consumer not recovered.**

## Stream input and callback

`ScreenStreamProcessData` (`jmcs`, VA `0x28e2c9`) forwards the generic stream pointer and process-data arguments via a global function pointer. Honda's registered callback family includes `ScreenStreamInitialize`, `Finalize`, `SetProperty`, `Start`, `Stop`, and `ProcessData`; `libcarplay_proxy.so` stores one global callback table. Honda's `mc_ScreenStreamProcessData` (`0xbee91`) parses/assembles input data and invokes callbacks in its implementation, but the bounded evidence does not establish a phone endpoint, stream ID, or a direct H.264-to-Android-surface consumer.

The native artifacts contain H.264 conversion/NAL helpers and `H264` strings, but no recovered decoder creation or Android `Surface`/window target in this CarPlay screen callback path. The independently measured Android/NVIDIA decoder probe is capability evidence only and is not the implementation consumer for this native stream.

## Callback argument evidence

| Identity/context | Callback provides? | Evidence |
|---|---|---|
| Screen ID | No explicit screen ID visible in generic `ScreenStreamProcessData` wrapper | High for wrapper signature; callback implementation may inspect context |
| Stream object | Yes | Generic wrapper receives stream pointer and forwards it |
| Session ID | Unknown | No decoded ID or explicit argument recovered |
| User/context pointer | Yes, structurally via stream context APIs | Context is stored at stream offset `+8`; semantic content unknown |
| Screen object pointer | Unknown | StartSession is invoked on receiver session object, but no proven callback context identity chain |

## Decoder/output ledger

| Item | Finding |
|---|---|
| Decoder creation/implementation | UNKNOWN in this path |
| Decoder type | H.264 handling exists; concrete decoder consumer UNKNOWN |
| Cardinality | UNKNOWN. A prior separate hardware probe instantiated two OMX decoders, but this does not prove this path uses those instances or supports concurrent CarPlay streams. |
| Surface owner/creation | UNKNOWN in this path |
| Surface passed to decoder | Not recovered |
| Screen/display association | UNKNOWN |
| Independent start/stop | Generic stream lifecycle callbacks exist; independent per-display behavior UNKNOWN |
| Second output surface structurally possible | UNKNOWN for this CarPlay consumer; the Android renderer canvas is a separate downstream capability |

This evidence is insufficient to claim singleton or per-stream decoder cardinality. Do not infer the Android output destination from the generic `ScreenStream` API.
