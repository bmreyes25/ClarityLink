# Honda primary CarPlay display/session path

**Scope:** static reconstruction from the copied Honda configuration and focused `jmcs`/proxy analysis. No Identification bytes or second-display exchange were captured. Static configuration is not equivalent to the live negotiated descriptor.

## Supported path

```text
j_config.xml CarPlay/ScreenProperties
  -> jmcs mc_carplay_app_init (VA 0xaff09)
  -> ScreenCreate(gMainScreen) (VA 0xaffd2)
  -> screen_add_props (VA 0xabd51)
  -> ScreenRegister(gMainScreen)
  -> AirPlayReceiverSessionScreen_CopyDisplaysInfo (VA 0x287ae1)
  -> ScreenCopyMain (VA 0x2a17fd; obtains registry index 0)
  -> property dictionary for the current main screen
```

The Honda initializer contains one `gMainScreen` creation/registration. The generic registry is an array, but the observed display-info function asks only for `ScreenCopyMain`; this is not a loop over all registered screens. `libcarplay_proxy.so` `mc_carplay_proxy_screen_register` (VA `0x1b7d`) stores one global 24-byte callback table and returns `0x16` when already registered. That is a separate singleton restriction at the stream callback boundary.

The saved full disassembly shows `_ScreenThread` (VA `0x283dad`) waiting on a semaphore, then calling `AirPlayReceiverSessionScreen_StartSession` (VA `0x2883a9`) at `0x283eb6` after a successful wake. `StartSession` initializes receiver session state, creates a generic `ScreenStream`, copies main-screen properties, configures the stream, and starts it. It is an internal lifecycle boundary; the upstream event/response, transport, request schema, and mapping from phone response to stream identity remain unresolved. `AirPlayReceiverSessionScreen_Setup` (`0x287d5d`) parses a dictionary-like input via helper `0x294598`, but its caller and input origin are not identified. See [screen-start-transport.md](screen-start-transport.md) and [Step 8](../../step-reports/08-screen-session-trace.md).

The bounded disassembly does not identify `_ScreenThread`'s creation site. Its visible worker path waits on a semaphore; on success it calls `StartSession`, then follows session processing and calls `AirPlayReceiverSessionScreen_StopSession` (`0x288451`, tail-calls internal cleanup helper `0x28795c`) before returning. A distinct screen teardown helper `_ScreenTearDown` (`0x284629`) also exists, but its external trigger/ownership is not established. Do not infer the creator or the event's protocol meaning from these functions alone.

| Property | Static primary value | Confidence / limit |
|---|---|---|
| Role | Main (`gMainScreen`, `ScreenCopyMain`) | HIGH CONFIDENCE locally; wire role encoding unknown |
| Pixel dimensions | 800×480 | HIGH CONFIDENCE in `j_config.xml`; negotiated value not captured |
| Maximum frame rate | 30 FPS | HIGH CONFIDENCE as configured; actual rate not observed |
| Touch | `TOUCH_MODE=1`, `hifi` | HIGH CONFIDENCE as configured; protocol encoding unknown |
| Physical size | 153×92 mm in `System/Display` | CONFIRMED local config; protocol mapping unproven |
| UUID | `displayUUID` property/function exists; no value/generation recovered | UNKNOWN |
| Session/stream ID | No primary value recovered | UNKNOWN |
| Codec | H.264 routines and `H264` strings exist in `jmcs` | HIGH CONFIDENCE that handling exists; negotiated profile/stream binding unknown |
| Session lifecycle | `ScreenStreamInitialize/Start/ProcessData/Stop/Finalize` callbacks exist; initializer stores a dispatch context and increments a generic stream counter | CONFIRMED API lifecycle; no observed per-display association |
| Display-info construction owner | `jmcs` `AirPlayReceiverSessionScreen_CopyDisplaysInfo` | CONFIRMED local code path; not proven to serialize iAP2 Identification |
| Transport owner | Not identified from available artifacts | UNKNOWN |
| Wire advertisement | Receiver constructs display-info properties from the main screen | HIGH CONFIDENCE local callback path; field encoding/framing/transport not recovered |

## Evidence boundary

`AirPlayReceiverSessionScreen_CopyDisplaysInfo` is the strongest observed display-info construction point. Its output is a CoreFoundation-style property dictionary assembled from `ScreenCopyMain` and property lookups. This is separate from the iAP2 Identification state machine. The available `jmcs` strings/symbols show iAP2 identification states but do not identify a numeric field schema or connect the screen dictionary to a specific iAP2 TLV.

The decoded video receiver is not fully traced from a phone response to a specific Android surface. Honda's proxy offers one registered screen callback table. No source evidence shows a second display role, UUID mapping, application assignment, or a stream/session ID that could route Display B independently.

Sources: [`j_config.xml`](../../extracted/system-vendor/system/vendor/media/mcs/j_config.xml), [`research/carplay-identification-model.md`](../carplay-identification-model.md), [`research/native/receiver-multidisplay-audit.md`](../native/receiver-multidisplay-audit.md), and [`step-reports/04-identification.md`](../../step-reports/04-identification.md).
