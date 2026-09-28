# Video stream binding trace

**Verdict: partial internal association; display-to-stream key UNKNOWN.**

## Proven path

`AirPlayReceiverSessionScreen_StartSession` (`jmcs`, VA `0x2883a9`) calls `ScreenStreamCreate` (`0x28e209`) with its supplied context, then configures/starts that stream through generic helper functions. Generic `ScreenStreamSetContext` stores a pointer at stream offset `+8`; `ScreenStreamGetContext` returns it. `ScreenStreamProcessData` dispatches through a global callback pointer and forwards the stream object plus buffer, length, timing/metadata arguments. Honda's `mc_ScreenStreamInitialize` (`0xbec19`) obtains a per-stream context with `ScreenStreamGetContext`, allocates/stores its own callback context with `ScreenStreamSetContext`, and increments `g_screen_streams_cnt`.

Honda's `mc_carplay_screen_stream_init_instance` (`0xbd199`) stores a `mc_carplay_screen_src_ifc` pointer and `g_mc_dp` context in its instance structure; this is receiver implementation context, not evidence of a display UUID or independent screen mapping. The separate `libcarplay_proxy.so` screen registration accepts one six-function callback table and rejects later registrations with observed return `0x16`.

## Binding ledger

| Question | Finding |
|---|---|
| Display-to-stream key | UNKNOWN. A screen-session object is passed into stream startup; stream context pointers exist, but no proven screen index, display UUID, session ID, or stream ID lookup key connects them. |
| Created by | Generic `ScreenStreamCreate` inside `AirPlayReceiverSessionScreen_StartSession` (high confidence). |
| Stored in | Generic stream object plus callback-owned context; Honda context details are partly visible in initialization (high confidence for pointers, unknown semantic mapping). |
| Looked up by | Generic dispatch calls registered function pointers with stream/context data. No display lookup recovered. |
| Unique per screen | UNKNOWN. The session creates a stream object, but Honda selects only `ScreenCopyMain` and the proxy callback table is singleton. |
| Multiple generic stream objects | YES, structurally: generic creation and `g_screen_streams_cnt` increment exist. This does not prove concurrent independent CarPlay display sessions. |
| Teardown | Generic `ScreenStreamStop`/`Finalize`, Honda callbacks and session stop/cleanup exist. Distinct-display teardown behavior is UNKNOWN. |

## Required next evidence

Trace the setup/event producer feeding `_ScreenThread`, the creation path that invokes `AirPlayReceiverSessionScreen_Setup`, and the parser/transport that provides its values. Then trace the stream object's callback context through Honda proxy dispatch to the concrete decoder. Until then, distinct stream identity and Display B isolation remain unproven.
