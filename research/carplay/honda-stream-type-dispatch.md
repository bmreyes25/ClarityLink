# Honda stream type request dispatch — Step 29

The incoming request body is decoded as a property list by `CFCreateWithPlistBytes` (`0x29354c`). `_connectionHandleMessage` passes the resulting request dictionary to `AirPlayReceiverSessionSetup` (`0x2854e0`). Setup reads `streams` as a CFArray and loops over its entries. Each entry's `type` is retrieved as an integer with `CFDictionaryGetInt64` at `0x28590e`.

Dispatch in Setup handles values 100 and 101 through audio setup, and 110 through `AirPlayReceiverSessionScreen_Setup` (type-110 branch around `0x28606e`/call at `0x28609c`). Values below 100 and unrecognized values—including 111—reach the unknown-type log at `0x2861f6`; the loop then increments and continues at `0x286220`. Type 111 has no setup handler, but Step 37 does not support saying it immediately aborts the entire transaction. Exact response/status for Type111-only and mixed arrays remains unresolved.

```text
KEY: streams[] element key `type`
CONVERSION: CFDictionaryGetInt64 -> integer
KNOWN ACCEPTED TYPES: 100, 101, 110
TYPE 110: screen setup, dynamic listener, response type=110/dataPort
TYPE 111: no case; log and skip/continue in the per-entry loop
REQUEST MODEL: array, per-entry loop
DEFAULT: log then continue; transaction outcome remains context-dependent
```

The SETUP handler appends a response entry per processed stream. This proves multi-entry mechanics, not that every duplicate or combination is accepted. The exact HTTP method/path route remains unresolved. See `honda-setup-request.md` and `honda-stream-type-parser.md`.
