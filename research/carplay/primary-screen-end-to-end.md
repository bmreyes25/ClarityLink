# Primary screen end-to-end trace

**Status: control path extended through TCP accept; H.264 decoder/output binding remains open.**

```text
CONTROL INPUT                                    MEDIA / OUTPUT
unknown dispatcher / session call               accepted session data
        |                                                  |
        v                                                  v
AirPlayReceiverSessionSetup                ScreenStreamProcessData
        |                                      global callback dispatch
        +-- AirPlayReceiverSessionScreen_Setup             |
        |   CFL dictionary value -> +0x10/+0x14            v
        +-- ServerSocketOpen -> listener fd +0x1418    mc_ScreenStreamProcessData
                      |                                      |
                      v                                      v
               _ScreenThread -> SocketAccept(select/accept) framed parser
                      |                                      |
                      v                                      v
        AirPlayReceiverSessionScreen_StartSession      helper 0x8e70c
                      |                                indirect callback [obj+0x10]
                      v                                      |
             ScreenStream create/start                     helper 0x8ea18
                      |                                      |
                      +---- session/stream binding ----------+? UNKNOWN
                                                             |
                       H.264/MediaCodec capability in jmcs   |
                       linkage to callback UNKNOWN ----------+
                                                             v
                                                decoder / output Surface UNKNOWN
```

## Edge ledger

| Edge | Status | Evidence |
|---|---|---|
| `AirPlayReceiverSessionSetup` -> `AirPlayReceiverSessionScreen_Setup` | CONFIRMED | direct call site `0x28609c` |
| Setup dictionary -> screen object `+0x10/+0x14` | CONFIRMED | `0x294598` -> `CFLDictionaryGetValue` and typed conversion |
| Setup -> listener at outer `+0x1418` | CONFIRMED | `ServerSocketOpen` (`0x2a0a34`) returns fd stored in field |
| listener -> `_ScreenThread` | CONFIRMED | `_ScreenThread` reads offset and calls `SocketAccept` (`0x2a0480`) |
| `SocketAccept` -> incoming peer | CONFIRMED | imported `select()` then `accept()` |
| successful accept -> `StartSession` | CONFIRMED | zero return branch calls `0x2883a8` at `0x283eb6` |
| StartSession -> generic ScreenStream lifecycle | CONFIRMED | existing trace at `0x28e208` / configure / start |
| ScreenStream -> Honda callback | CONFIRMED at generic ABI | global callback dispatch in `ScreenStreamProcessData` |
| Honda callback -> `0x8e70c` framed dispatch | CONFIRMED | two call sites in `mc_ScreenStreamProcessData` |
| callback -> H.264 pipeline/MediaCodec | UNKNOWN | same ELF has H.264 and MediaCodec APIs, but no proven object/call xref from this callback |
| decoder -> output Surface | UNKNOWN | no CarPlay-specific output binding recovered |

No shared `screenSession` context has yet been proven across Setup and media dispatch. The generic stream context API exists, but its assignment and semantic identity remain unresolved. Display B remains blocked by the missing link from accepted session/request through stream identity to independent decoder/output routing.
