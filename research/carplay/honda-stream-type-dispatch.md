# Honda stream type request dispatch — Step 29

The incoming request body is decoded as a property list by `CFCreateWithPlistBytes` (`0x29354c`). `_connectionHandleMessage` passes the resulting request dictionary to `AirPlayReceiverSessionSetup` (`0x2854e0`). Setup reads `streams` as a CFArray and loops over its entries. Each entry's `type` is retrieved as an integer with `CFDictionaryGetInt64` at `0x28590e`.

Dispatch in Setup handles values 100 and 101 through audio setup, and 110 through `AirPlayReceiverSessionScreen_Setup` (`0x28609c`). Values below 100 and unrecognized values—including 111—reach the invalid-type log/error path at `0x2861f6` and common cleanup. Honda's Type-111 behavior is therefore rejected by this dispatcher; no generic setup fallback was found. Exact external status mapping is not asserted.

```text
KEY: streams[] element key `type`
CONVERSION: CFDictionaryGetInt64 -> integer
KNOWN ACCEPTED TYPES: 100, 101, 110
TYPE 110: screen setup, dynamic listener, response type=110/dataPort
TYPE 111: invalid-type path
REQUEST MODEL: array, per-entry loop
DEFAULT: invalid type path
```

The SETUP handler appends a response entry per processed stream. This proves multi-entry mechanics, not that every duplicate or combination is accepted. The exact HTTP method/path route remains unresolved. See `honda-setup-request.md` and `honda-stream-type-parser.md`.
