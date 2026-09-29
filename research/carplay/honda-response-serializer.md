# Honda response serializer boundary

## Recovered serializer candidates

Honda `jmcs` includes generic property-list serialization. `_requestSendPlistResponse` (`0x289f60`) takes a property-list object in `r2`, calls `CFPropertyListCreateData` (`0x28e6fc`), obtains bytes and length from the returned `CFData`, calls `HTTPMessageSetBody` (`0x29d01c`), and releases the temporary data. It sets an HTTP response status and reports an error through an output pointer.

This proves a local HTTP plist serializer ABI for that helper, **not** that it serializes `AirPlayReceiverSessionSetup` responses. No reference/call edge from the setup response delegate to `_requestSendPlistResponse`, `CFPropertyListCreateData`, `CFBinaryPlistCreateData`, or a network write was recovered in the bounded offline trace.

| ABI property | `_requestSendPlistResponse` | CarPlay SETUP response |
|---|---|---|
| Input object | generic CF-style plist object | mutable dictionary published by Setup |
| Output | serialized CFData copied into HTTPMessage body | unknown encoder/output |
| Format | `CFPropertyListCreateData` with format argument `0xc8`; exact format enum confirmation is outside this trace | unknown |
| Ownership | returned CFData locally held then `CFRelease`d after body setter | unknown at callback boundary |
| Mutability before serialization | input object is supplied to serializer; helper itself does not mutate it | Setup's local dictionary is mutable before callback; callback mutation contract unknown |
| Network write | HTTPMessage body is prepared; downstream send is not part of this helper | unknown |

## Finding

```text
SERIALIZER: _requestSendPlistResponse (0x289f60), generic HTTP plist path only
SETUP RESPONSE SERIALIZER: UNKNOWN
PRE-SERIALIZATION RESPONSE MUTABLE: local response accumulator YES; hook-visible mutability UNKNOWN
HOOK AT SERIALIZER PRE-CALL: not selected; no proven serializer/call edge for this response
```

Do not install an interposer at this generic HTTP helper based only on its plist behavior.
