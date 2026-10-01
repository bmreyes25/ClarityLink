# Honda display capability phone-facing path — current status

**Static path:** confirmed by Step 32. **Live phone transaction:** not observed. **Safe runtime hook:** not established.

## Recovered dataflow

```text
_connectionHandleMessage /info dispatch (0x28b678–0x28b68e)
 -> _requestProcessInfo (0x28a018)
 -> AirPlayCopyServerInfo (0x282cd4; call 0x28a156)
 -> same result passed to _requestSendPlistResponse (0x289f60; call 0x28a19c)
 -> binary plist format 0xc8
 -> HTTPConnectionSendResponse (0x29dbe4; caller 0x28b790)
 -> SocketWriteData (0x2a01c0) -> writev@plt
```

The returned `serverInfo["displays"]` value therefore reaches the phone-facing `/info` response in static code flow. This is distinct from evidence about SETUP even though both use the plist response helper. See [Step 32](../../step-reports/32-airplay-info-phone-path.md).

## Display construction

```text
AirPlayCopyServerInfo (0x282cd4)
 -> AirPlayReceiverSessionPlatformCopyProperty("displays") (0x28d328)
 -> AirPlayReceiverSessionScreen_CopyDisplaysInfo (0x287ae0)
 -> mutable one-element CFArray [main display dictionary]
 -> returned CFDictionaryRef
```

The property callback creates a mutable array and calls `ScreenCopyMain()` once to append one descriptor. The descriptor fields recovered from the exact matching jmcs binary are `edid`, `features`, `maxFPS`, physical/pixel dimensions, and numeric `uuid`. See [descriptor recovery](honda-copy-displays-info.md) and the [Step 43A Type111 differential](honda-info-type111-differential.md).

## Step 31 historical note

Step 31 had not recovered the server-info consumer, so the report then marked phone-facing use unknown. Step 32 recovered the `/info` route, callsite, serialization, and send path; it supersedes the Step 31 status. The original Step 31 report remains intact as history.

## Mutation boundary and limitations

The server-info return is held between `AirPlayCopyServerInfo` return at callsite `0x28a156` and serializer call `0x28a19c`. That is a structurally mutable interval in the analyzed path, not validation of an executable hook's ABI, collection ownership, deployment, or failure behavior.

```text
LOCAL DISPLAYS VALUE: CONFIRMED
INSERTED INTO SERVER INFO: CONFIRMED
PASSED TO /info PLIST SERIALIZER: CONFIRMED
SENT THROUGH HTTP/SocketWriteData PATH: CONFIRMED statically
LIVE PHONE TRANSACTION OBSERVED: NO
SAFE EXECUTABLE HOOK: NOT ESTABLISHED
```

Do not infer that this makes Type111 implementable. Honda's second-descriptor requirements, Type111 request/response schema, security, display/stream correlation, jmcs integration seam, and ExternalDisplay frame handoff remain unresolved.
