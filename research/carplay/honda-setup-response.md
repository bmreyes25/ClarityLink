# Honda CarPlay SETUP response trace

**Scope:** offline static analysis of the local ignored `extracted/system-vendor/system/bin/jmcs` ELF. No vehicle, ADB, firmware modification, or interposer work. The binary hash and address conventions are in [jmcs-address-map.md](jmcs-address-map.md).

## Result

Honda's `AirPlayReceiverSessionSetup` (`0x2854e0`, Thumb symbol `0x2854e1`) is a status-returning routine. It receives a dictionary-like request, constructs mutable CF-style dictionaries, creates a TCP listener, and on success adds a stream dictionary to a response-like local container before invoking the registered session callback. This is a concrete Honda SETUP response model, but the callback's phone-facing transport encoder is not yet identified. Therefore it is **not proven** that this local response dictionary is the object serialized and sent to the iPhone.

```text
request CFDictionary-like object
  -> AirPlayReceiverSessionSetup (0x2854e0)
  -> create mutable response dictionary (0x28557e)
  -> create mutable stream dictionary (0x286086)
  -> insert type=110 and dataPort=<dynamic port> (0x28614a..0x286160)
  -> _AddResponseStream (0x284db8): append stream dict to "streams" CFArray
  -> store response dict through output pointer (0x286260)
  -> completion callback receives status/context (0x2862b0; not the response object)
  -> caller consuming output dictionary / transport serializer: unresolved
```

### ABI and observed objects

| Item | Finding | Confidence |
|---|---|---|
| Setup request | CF-style dictionary; Setup reads typed values and nested dictionaries/arrays via `CFDictionaryGet*` helpers | **HONDA CONFIRMED** for local type family; upstream wire parser edge incomplete |
| Setup response accumulator | mutable CF-style dictionary at local stack slot `sp+0x28` | **HONDA CONFIRMED** |
| Stream entry | mutable CF-style dictionary | **HONDA CONFIRMED** |
| Stream collection | CFArray under key `streams`; helper `_AddResponseStream` creates mutable array if absent and appends the entry | **HONDA CONFIRMED** |
| Stream type | integer `110` inserted under key `type` | **HONDA CONFIRMED** |
| Stream port | dynamically bound TCP port inserted under key `dataPort` | **HONDA CONFIRMED** |
| Completion callback | delegate callback receives status and callback context; response dictionary is not passed in its arguments | **HONDA CONFIRMED** |
| Callback serializer / transport write | not mapped from the delegate slot to an encoder/network write | **UNKNOWN** |
| Primary display descriptor in SETUP response | no descriptor insertion edge proven; this routine adds a stream response entry | **UNKNOWN** |

The exact instruction sites are `CFDictionaryCreateMutable` at `0x28557e` and `0x286086`, key/value insertions at `0x286152` and `0x286160`, `_AddResponseStream` at `0x286168`, and output/callback dispatch at `0x286260` and `0x2862b0`. `_AddResponseStream` at `0x284db8` calls `CFDictionaryGetTypedValue` for `streams`, `CFArrayCreateMutable`, `CFArrayAppendValue`, and `CFDictionarySetValue`.

### End-to-end boundary

`AirPlayReceiverSessionSetup` returns an `OSStatus`, not a response object. Its caller-visible response path uses an output pointer (argument initially in `r2`, saved at entry) to publish the locally built dictionary. A later completion callback receives status and callback context; the disassembly does not pass it the response dictionary. Exact C prototype parameters are absent from the available DWARF subprogram DIE, so the complete public ABI signature and ownership contract are not reconstructed. The generated AAPCS32 code shows ordinary ARM EABI register/stack argument passing.

`_requestSendPlistResponse` (`0x289f60`) is a separate generic HTTP helper. It accepts a CF-style plist object, invokes `CFPropertyListCreateData` (`0x28e6fc`), obtains `CFData` bytes/length, and calls `HTTPMessageSetBody` (`0x29d01c`); it releases the temporary serialized `CFData`. No static call/reference proves that this helper is the session delegate used by `AirPlayReceiverSessionSetup`. Do not identify it as the CarPlay SETUP serializer without that edge.

### Direct answers

```text
REQUEST OBJECT TYPE: CF-style property-list dictionary (local parser/input edge incomplete)
RESPONSE OBJECT TYPE: mutable CF-style dictionary
DISPLAY CONTAINER TYPE: CopyDisplaysInfo returns one CF-style dictionary; SETUP stream entries are a CFArray
RESPONSE BUILDER: AirPlayReceiverSessionSetup + _AddResponseStream
SERIALIZER: unknown for this session response; separate HTTP plist helper exists at 0x289f60
RETURN PATH: response dictionary out-parameter -> caller (unknown consumer); separate completion callback receives status/context
PRE-SERIALIZATION RESPONSE MUTABLE: yes within Setup; mutation by an interposer at delegate time unknown
PHONE-FACING SERIALIZATION PROVEN: no
```

The main display's local values (800×480, 30 FPS, high-fidelity touch, and 153×92 mm) are configuration evidence only. No recovered SETUP stream entry includes those geometry values. Primary UUID source/value and response-level display list remain unknown. The stream array shows Honda's response representation can contain multiple stream dictionaries structurally; it does **not** prove that Honda will accept a Type-111 request, support more than one display descriptor, or tolerate an extra entry.

## Sources

- Local ELF: `extracted/system-vendor/system/bin/jmcs` (ignored; do not stage); see [address map](jmcs-address-map.md).
- Existing listener trace: [screen-tcp-listener.md](screen-tcp-listener.md).
- Local display construction: [primary-display-session.md](primary-display-session.md).
- Prior art only: [stream-type-111.md](stream-type-111.md), [altscreen-data-port.md](altscreen-data-port.md).
