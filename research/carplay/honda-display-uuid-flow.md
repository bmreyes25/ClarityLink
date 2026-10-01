# Honda display UUID flow — Steps 33 and 43B

The main display descriptor's `uuid` value is read from a property on the object returned by `ScreenCopyMain()` inside `AirPlayReceiverSessionScreen_CopyDisplaysInfo` (`0x287ae0`). The builder inserts the value under `uuid` via `CFDictionarySetInt64`; it is therefore represented as a numeric CF value in this observed construction path. The source property’s underlying storage type, generation, stability, and scope are unknown.

Step 32 proves this descriptor is nested in `serverInfo["displays"]` and the same server-info object reaches `_requestSendPlistResponse` for `/info`. Phone-facing serialization is confirmed statically.

In the analyzed Setup path, no display UUID is read from a Type-110 stream dictionary, copied into its response, used in the Type-110 crypto derivation, or compared with `streamConnectionID`. The Setup path reads a distinct 64-bit `streamConnectionID` and supplies it to `AirPlay_DeriveAESKeySHA512ForScreen`. No UUID/connection-ID association structure was recovered.

| Property | Finding |
|---|---|
| Source object | `ScreenCopyMain()` result |
| Source property | `uuid` accessor/property; backing representation unknown |
| Descriptor insertion | numeric `CFDictionarySetInt64` under `uuid` |
| Phone-facing | Confirmed via `/info` server-info serializer path |
| Static, generated, or session-scoped | Generated/default path is a candidate; actual advertised source and stability unknown |
| Used by Honda SETUP | No use found in analyzed Type-110 path |
| Bound to `streamConnectionID` | No link found |

No UUID consumer was linked to an analyzed SETUP/Type-110 stream or second-display state; this is scoped to recovered dataflow. Do not invent a UUID string or assert that it selects the screen stream. See `stream-connection-id.md` and `display-stream-correlation.md`.

## Step 43D identity-layer update

The deeper Setup trace confirms separate field paths: `/info` inserts the numeric Screen `uuid`; SETUP dispatches on stream `type`; Type-110's nonzero `streamConnectionID` is an input to screen crypto derivation; and the response advertises a listener through `dataPort`. No UUID read/comparison/derivation was found in those traced Setup paths. This supports a **working search model** that display capability identity and stream/session/crypto identity should be traced separately. Honda's actual semantic role for `uuid` (presentation versus HID/input identity) remains `HONDA_UNKNOWN`; the more specific UUID-to-HID claim is external prior art only. See [Step 43D](../../step-reports/43d-setup-stream-identity-correlation.md) and [the pinned prior-art note](setup-stream-identity-prior-art.md).
