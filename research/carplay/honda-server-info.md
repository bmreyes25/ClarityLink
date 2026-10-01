# Honda AirPlayCopyServerInfo — current recovered path

**Current status:** Step 32 supersedes the earlier Step 30/31 uncertainty. The phone-facing `/info` call/dataflow is confirmed statically. The original Step 31 report remains historical; see [Step 32](../../step-reports/32-airplay-info-phone-path.md). The field-by-field xcertplay comparison is in [Step 43A](honda-info-type111-differential.md).

## Step 32: phone-facing consumer recovered

`_requestProcessInfo` (`0x28a018`) calls `AirPlayCopyServerInfo` at `0x28a156`; the returned dictionary is passed unchanged in `r2` to `_requestSendPlistResponse` at `0x28a19c`. `_connectionHandleMessage` selects the info handler via the `/info` suffix branch and later calls `HTTPConnectionSendResponse` at `0x28b790`. The serializer synchronously creates the binary plist body (format `0xc8`); `_requestProcessInfo` releases the same dictionary at `0x28a1da` after serialization. Therefore the `displays` array is phone-facing in the static dataflow. The structurally mutable window is return at `0x28a156` through serializer entry at `0x28a19c`. Details: [Step 32](../../step-reports/32-airplay-info-phone-path.md).

## Historical Step 31 result (superseded)

Step 31 did not recover the consuming handler and correctly left phone-facing use unknown on its evidence at that time. Step 32 later recovered `_connectionHandleMessage` `/info` dispatch into `_requestProcessInfo`, the `AirPlayCopyServerInfo` call, and the same returned dictionary reaching the binary-plist serializer. The current conclusion is therefore **phone-facing `/info` dataflow confirmed statically**, not unknown. The Step 31 report is retained as history and its conclusions must not be used as the current status.

**Evidence:** authoritative local jmcs ELF, SHA-256 cbc7ba881648fb8ffdfcc4c1100a028345c37134a2ae3b9dff7d76572851c232. Offline static analysis only.

## Function and contract

AirPlayCopyServerInfo is at 0x282cd4 (size 0x8c4). DWARF identifies its declaration in AirPlayReceiverServer.c:156:

```c
CFLDictionaryRef AirPlayCopyServerInfo(
    AirPlayReceiverSessionRef inSession,
    CFLArrayRef inProperties,
    uint8_t *inMACAddr,
    OSStatus *outErr);
```

It returns a server-info dictionary (or null on failure); outErr is optional and receives the error status. The builder creates a mutable CF dictionary and populates it from server/session properties and local device/configuration values. It is not itself a serializer or network-send routine.

## Session property query and displays insertion

At 0x282e34, the function calls AirPlayReceiverSessionPlatformCopyProperty with inSession and the CF string key displays. If a value is returned, CFDictionarySetValue inserts that exact object into the result dictionary under the same key at 0x282e42; the temporary copied reference is released at 0x282e48 after insertion.

```text
AirPlayCopyServerInfo
  -> AirPlayReceiverSessionPlatformCopyProperty("displays")
  -> CFDictionarySetValue(serverInfo, "displays", returnedValue)
```

AirPlayReceiverSessionPlatformCopyProperty (0x28d328) compares the key at 0x28d332–0x28d342. Its displays branch creates a mutable CFArray, calls AirPlayReceiverSessionScreen_CopyDisplaysInfo (0x287ae0), appends the returned main-display dictionary, and returns the array. Thus the builder inserts the one-element array returned by that branch.

## Recovered callers and transport status

`_requestProcessInfo` calls the function at `0x28a156`; the returned object is passed at `0x28a19c` to `_requestSendPlistResponse`. The `/info` route later sends that response through the HTTP state machine and `SocketWriteData`/`writev`. This is distinct from the separately analyzed SETUP object, although both use the synchronous binary-plist response helper. See Step 32 for register/dataflow detail.

## Ownership and mutation

The builder creates a mutable server-info dictionary. The displays array is created with CFArrayCreateMutable. The main descriptor dictionary is mutable as well. The callback returns a copied/owned value; AirPlayCopyServerInfo inserts it into the mutable result dictionary, then releases its temporary ownership. Step 32 separately proves this object reaches the phone-facing `/info` serializer. Local mutability does not prove a safe executable hook or deployment path.

| Decision | Result |
|---|---|
| Server-info return type | CFLDictionaryRef |
| Displays query | Confirmed, property key displays |
| Displays insertion | Confirmed in returned dictionary |
| Server-info dictionary mutable during construction | Yes |
| Displays container mutable | Yes, CFMutableArray |
| Phone-facing server-info path | Confirmed statically by Step 32 |
| Descriptor field inventory | See `honda-copy-displays-info.md` and Step 43A differential |
| Safe executable hook | Not established; a structural mutable-object interval is not runtime hook validation |

See honda-display-capability-send-path.md, honda-display-capabilities.md, and Step 30.
