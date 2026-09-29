# Honda display capability send path — Step 30

## Step 32: complete path

```text
_connectionHandleMessage /info dispatch (0x28b678–0x28b68e)
 -> _requestProcessInfo (0x28a018)
 -> AirPlayCopyServerInfo (0x282cd4; call 0x28a156)
 -> same result passed to _requestSendPlistResponse (0x289f60; call 0x28a19c)
 -> binary plist format 0xc8
 -> HTTPConnectionSendResponse (0x29dbe4; caller 0x28b790)
 -> SocketWriteData (0x2a01c0) -> writev@plt
```

This closes the static network edge: the nested `serverInfo["displays"]` value reaches the phone-facing response serializer. See [Step 32](../../step-reports/32-airplay-info-phone-path.md).

## Step 31 consumer search

The builder is not dynsym-exported, and no normal ELF import was found among the 45 mapped shared libraries. Generic `dlopen`/`dlsym` use has no matching runtime lookup key. Reverse tracing confirms that the known plist/HTTP/writev path carries SETUP output only. `DISPLAYS_PHONE_FACING` and the phone-facing mutation point remain UNKNOWN. See [consumer search](airplay-server-info-consumers.md).

## Proven local path

```text
AirPlayCopyServerInfo (0x282cd4)
  -> AirPlayReceiverSessionPlatformCopyProperty("displays") (0x28d328)
  -> AirPlayReceiverSessionScreen_CopyDisplaysInfo (0x287ae0)
  -> mutable one-element CFArray [main display dictionary]
  -> CFDictionarySetValue(serverInfo, "displays", array) (0x282e42)
  -> returned CFDictionaryRef
```

The displays property comparison and mutable array construction are in the platform property callback at 0x28d332–0x28d370; the main display object is appended at 0x28d37a–0x28d382. The server-info builder queries and inserts this property at 0x282e34–0x282e48.

## Unproven network edge

No caller of AirPlayCopyServerInfo was found in the analyzed direct call sites, and the available evidence does not resolve its indirect consumer, incoming request, server-info serializer, HTTP/control response body, or socket send. The confirmed _connectionHandleMessage/binary-plist/writev chain belongs to AirPlayReceiverSessionSetup; it is not evidence for AirPlayCopyServerInfo.

```text
LOCAL DISPLAYS VALUE: CONFIRMED
INSERTED INTO SERVER INFO DICTIONARY: CONFIRMED
SERIALIZED TO A RESPONSE: UNKNOWN
SENT TO IPHONE: UNKNOWN
```

Accordingly, DISPLAYS_PHONE_FACING = UNKNOWN. A function name and a local dictionary insertion do not establish that the object is advertised to the phone.

There is no proven latest safe phone-facing mutation point. The builder output is locally mutable, but hook A cannot be placed defensibly until its consumer and serialization boundary are recovered. Do not infer the SETUP serializer handles server info.
