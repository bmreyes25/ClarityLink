# Honda AltScreen gap analysis

## Current Honda evidence

The tracked analysis confirms `AirPlayReceiverSessionSetup` calls `AirPlayReceiverSessionScreen_Setup`; Honda's screen setup reads a local configuration dictionary. `AirPlayReceiverSessionScreen_CopyDisplaysInfo` obtains `ScreenCopyMain` and builds properties for one main display. Honda initialization creates/registers one `gMainScreen`. The proxy `mc_carplay_proxy_screen_register` stores a singleton callback table and reports already-registered on a second registration. The AirPlay screen path later calls `mc_dev_attach("CarPlay Screen", ...)`, but the winning runtime backend remains unknown.

The listener binds ephemeral TCP and accepts a connection. The first `recv` request is 128 bytes; this is buffer length only, not proven framing. No Honda Type-111 request, display UUID, serialized descriptor, response port, or stream-to-decoder edge is recovered. See `primary-display-session.md`, `screen-tcp-listener.md`, `screen-tcp-framing.md`, `primary-screen-end-to-end.md`, and `display-b-interposer.md`.

## Direct map

| Prior art | Honda candidate | Classification |
|---|---|---|
| stock session setup delegate | `AirPlayReceiverSessionSetup` | DIRECT EQUIVALENT at symbol/call-path level |
| per-screen setup | `AirPlayReceiverSessionScreen_Setup` | DIRECT EQUIVALENT for current primary; B behavior unknown |
| stream 110 | current Honda primary | LIKELY EQUIVALENT; serialized type not recovered |
| stream 111 | no recovered Honda handler | NO HONDA EQUIVALENT YET |
| display descriptor list | `ScreenCopyMain` property dictionary | LIKELY EQUIVALENT boundary, but one-screen behavior observed |
| ephemeral data port | Honda `bind(0)`/`getsockname`/`CFDictionarySetInt64` | DIRECT EQUIVALENT mechanism for primary only; key and wire response unknown |
| Start / teardown | `StartSession`, `StopSession`, `_ScreenTearDown` | DIRECT EQUIVALENT lifecycle symbols; external trigger/request mapping unknown |
| secondary H.264 receiver | ClarityLink-owned future listener/decoder | NO HONDA EQUIVALENT YET |
| secondary render target | Honda ExternalDisplay View host | LIKELY EQUIVALENT output abstraction; privileged root/lifecycle integration missing |
| control/keyframe routing | Honda control callbacks | UNKNOWN |

## Decision

The registry lookup is bypassed **only if** Honda accepts a Type-111 request and ClarityLink can expose its own listener from the corresponding SETUP response. No Honda code evidence yet proves either condition. Therefore `mc_dev_attach` is **fallback only as an investigation**, not a protocol prerequisite, but it is premature to remove it as a project concern. The immediate gate is to identify the Honda display serialization / AirPlay SETUP boundary and whether it is safely interposable without breaking the singleton primary callback.

Honda native AltScreen support: **UNKNOWN**, not absent. Existing evidence proves one main display path; it does not prove receiver-wide incompatibility.
