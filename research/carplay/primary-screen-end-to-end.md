# Primary screen end-to-end trace

**Status: partial; both transport/event and decoder/output boundaries remain open.**

```text
CONTROL INPUT                         MEDIA / OUTPUT
unknown transport/parser              unknown video input source
        |                                      |
        v                                      v
AirPlayReceiverSessionSetup            mc_ScreenStreamProcessData
        |                                      |
        v                                      v
AirPlayReceiverSessionScreen_Setup      generic ScreenStream callback dispatch
  caller VA 0x28609c                            |
  structured lookup helper                      v
        |                                decoder: UNKNOWN
        v                                      |
receiver fields +0x10/+0x14                    v
        |                                  output Surface: UNKNOWN
        v
event producer/signal: UNKNOWN
        |
        v
_ScreenThread waits via helper 0x2a0480
        |
        v
AirPlayReceiverSessionScreen_StartSession
        |
        v
ScreenStreamCreate -> configure -> ScreenStreamStart
```

## Edge ledger

| Edge | Status | Evidence |
|---|---|---|
| `AirPlayReceiverSessionSetup` -> `AirPlayReceiverSessionScreen_Setup` | CONFIRMED | Direct call at `jmcs` VA `0x28609c` |
| Setup input -> stored receiver fields | CONFIRMED | Helper `0x294598`; writes at receiver offsets `+0x10/+0x14`; semantic field names unknown |
| Setup -> wait object signal | UNKNOWN | No signal producer/xref in focused artifacts |
| wait helper -> `_ScreenThread` start branch | CONFIRMED | `_ScreenThread` calls `0x2a0480`; zero return reaches StartSession call |
| `_ScreenThread` -> `StartSession` | CONFIRMED | Call at `0x283eb6` |
| `StartSession` -> generic stream create/configure/start | CONFIRMED | `0x28e208`, property/context helpers, `0x28e298` |
| `ScreenStream` -> Honda callback dispatch | CONFIRMED at generic ABI | Global callback dispatch; singleton Honda proxy table |
| Honda callback -> concrete decoder | UNKNOWN | No proven decoder call edge |
| decoder -> output Surface | UNKNOWN | No proven output-object edge |

## Boundaries

The Setup caller is now known, but the external/control-channel entry above `AirPlayReceiverSessionSetup`, the exact input object class/schema, and the wake producer remain unknown. Downstream, `mc_ScreenStreamProcessData` parses structured input but the H.264 frame receiver, decoder object, decoder cardinality, and Android Surface are unknown. No stream/display binding token is evident in the supported trace.

Minimum conceptual Display B insertion points remain: (1) descriptor/setup production and session assignment, and (2) per-stream callback/decoder/output routing. The current Honda singleton callback table is a material constraint. These points are hypotheses for investigation, not a supported interposer design.

**Second session structurally possible:** UNKNOWN. **Display-B interposer:** PLAUSIBLE as an investigation architecture, implementation blocked. **Raw capture:** HELPFUL only after the control endpoint is identified; an Identification-only capture is insufficient. No broad USB capture is indicated by current evidence.
