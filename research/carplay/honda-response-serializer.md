# Honda response serializer boundary

## Setup-specific serializer

The phone-facing caller `_connectionHandleMessage` (`0x28a30c`) passes its Setup output slot (`sp+0x54`) directly to `_requestSendPlistResponse` (`0x289f60`) as the property-list object argument (`r2`) at `0x28afba`.

The helper initializes an HTTP 200 response, calls `CFPropertyListCreateData` with format value `0xc8`, obtains byte pointer and length from the returned `CFData`, and calls `HTTPMessageSetBody`. The implementation's content-type constant is `application/x-apple-binary-plist`; value `0xc8` is the binary plist format. It releases its temporary `CFData` after body installation.

## Boundary and limits

This is no longer a generic-helper-only inference: a direct call edge connects Setup's exact output object to the serializer. Thus the same response dictionary containing the `streams` array and stock type-110/dataPort entry reaches serialized response bytes. The enclosing dispatcher sends the HTTP response through `HTTPConnectionSendResponse` (`0x29dbe4`). `_HTTPConnectionRunStateMachine` (`0x29d698`) calls `SocketWriteData` (`0x2a01c0`), which issues `writev@plt` on the connection descriptor and tracks partial writes. Static tracing reaches the TCP write syscall.

```text
SERIALIZER: _requestSendPlistResponse (0x289f60)
INPUT: Setup output CF-style dictionary, same caller stack slot
OUTPUT: binary property-list CFData installed as HTTP message body
FORMAT: binary plist (format argument 0xc8; application/x-apple-binary-plist)
STATUS: HTTP 200 on successful body construction
SETUP RESPONSE PHONE-FACING: CONFIRMED static call/dataflow
PRE-SERIALIZER MUTATION WINDOW: exists synchronously after Setup returns; hook safety still unproven
```
