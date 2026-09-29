# Honda SETUP request parsing — Step 29

## Body and request dictionary

`_connectionHandleMessage` (`0x28a30c`) dispatches the HTTP request. It calls `CFCreateWithPlistBytes` (`0x29354c`) at `0x28aca4` with the request body bytes and length; the helper creates CFData and calls `CFPropertyListCreateWithData` (`0x28e72a`) to decode the property list. The parsed dictionary is passed as `r1` to `AirPlayReceiverSessionSetup` (`0x2854e0`), with the session in `r0` and response output slot in `r2`, at `0x28af72`. The body allocation/ownership and exact HTTP method/path predicate are not resolved in this pass.

## Setup request reads

Top-level reads include `osBuildVersion` (string), `modelCode` (typed value), `udid` (typed value), and `streams` (typed CFArray). The handler obtains the array count and loops over each element with `CFArrayGetTypedValueAtIndex`. Each stream dictionary reads integer `type` using `CFDictionaryGetInt64` at `0x28590e`. This is an array/list request model, with per-element processing.

Other recovered stream fields include `audioFormat`, `audioLatencyMs`, conditional `audioBufferMainAltWiredMs` / `audioBufferMainAltWiFiMs`, and `dataPort` in the type-100 audio path. These are not evidence for screen UUID correlation. A `streamConnectionID` string exists elsewhere in the image, but no Setup read/write was recovered here.

The serializer/send path for the response remains as established in Step 27: the same response dictionary is passed to `_requestSendPlistResponse` after Setup. Exact HTTP route method/path and request object ownership remain open.
