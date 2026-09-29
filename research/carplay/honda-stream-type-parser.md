# Honda request stream type parser — Step 29

## Step 30 clarification

The invalid-type path for 111 begins at 0x2861f6 within AirPlayReceiverSessionSetup (0x2854e0). Exact external error/status mapping and all effects in a multi-entry request remain unresolved; do not claim a particular HTTP status. The narrow conceptual intercept is at the per-entry type dispatch, before the stock accepted cases/default. This is not a validated live hook ABI. See honda-type111-rejection.md.

## Exact extraction and dispatch

`AirPlayReceiverSessionSetup` reads `streams` as a CFArray, iterates its elements, and extracts each element's `type` with `CFDictionaryGetInt64` at `0x28590e`. The value is an integer held in the per-iteration local register/dataflow.

Dispatch accepts type 100 and 101 into audio setup branches and type 110 into the screen branch. Values below 100 and all other values—including 111—reach the invalid-type log/error path beginning at `0x2861f6`, followed by common cleanup/return. No generic screen setup is performed for 111. Exact external status mapping is not asserted here.

| Result | Evidence |
|---|---|
| Request key | `streams[]` element key `type` |
| Value type | Integer via `CFDictionaryGetInt64` |
| Dispatch | `AirPlayReceiverSessionSetup` (`0x2854e0`) |
| Accepted values | 100, 101, 110 |
| Type 110 target | `AirPlayReceiverSessionScreen_Setup`, call at `0x28609c` |
| Type 111 | Explicitly falls through invalid-type branch |
| Request model | Array, per-entry loop |
| Multiple entries | Iteration and per-entry response append are implemented; duplicate/type-combination constraints unresolved |

The response stream for type 110 includes type 110 and a dynamic listener `dataPort`. No request UUID, stream ID, or `streamConnectionID` correlation is established.
