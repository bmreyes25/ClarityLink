# Honda display UUID flow — Step 33

The main display descriptor's `uuid` value is read from a property on the object returned by `ScreenCopyMain()` inside `AirPlayReceiverSessionScreen_CopyDisplaysInfo` (`0x287ae0`). The builder inserts the value under `uuid` via `CFDictionarySetInt64`; it is therefore represented as a numeric CF value in this observed construction path. The source property’s underlying storage type, generation, stability, and scope are unknown.

Step 32 proves this descriptor is nested in `serverInfo["displays"]` and the same server-info object reaches `_requestSendPlistResponse` for `/info`. Phone-facing serialization is confirmed statically.

In the analyzed Setup path, no display UUID is read from a Type-110 stream dictionary, copied into its response, used in the Type-110 crypto derivation, or compared with `streamConnectionID`. The Setup path reads a distinct 64-bit `streamConnectionID` and supplies it to `AirPlay_DeriveAESKeySHA512ForScreen`. No UUID/connection-ID association structure was recovered.

| Property | Finding |
|---|---|
| Source object | `ScreenCopyMain()` result |
| Source property | `uuid` accessor/property; backing representation unknown |
| Descriptor insertion | numeric `CFDictionarySetInt64` under `uuid` |
| Phone-facing | Confirmed via `/info` server-info serializer path |
| Static, generated, or session-scoped | Unknown |
| Used by Honda SETUP | No use found in analyzed Type-110 path |
| Bound to `streamConnectionID` | No link found |

Do not invent a UUID string or assert that it selects the screen stream. See `stream-connection-id.md` and `display-stream-correlation.md`.
