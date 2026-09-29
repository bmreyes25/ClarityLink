# Honda SETUP dataPort field

**Status: Honda field and local insertion confirmed; transport serialization remains unproven.**

## Recovered path

```text
ServerSocketOpen (0x2a0a34), called at Setup 0x28611e
  -> TCP socket, requested port 0
  -> getsockname / SockAddrGetPort in helper
  -> assigned primary port in stack output at Setup sp+0x68
  -> CFDictionarySetInt64(streamEntry, "dataPort", assignedPort) at 0x286160
  -> CFDictionarySetInt64(streamEntry, "type", 110) at 0x286152
  -> _AddResponseStream(response, streamEntry) at 0x286168
  -> response['streams'] CFArray append at helper 0x284db8
  -> output dictionary / registered session callback at 0x286260 / 0x2862b0
  -> phone-facing serializer: UNKNOWN
```

| Question | Finding | Confidence |
|---|---|---|
| Dictionary | per-stream mutable CF-style dictionary | **HONDA CONFIRMED** |
| Key | `dataPort` | **HONDA CONFIRMED** from local constant string/xref and `CFDictionarySetInt64` call |
| Value | dynamic TCP port returned by bind-to-zero/getsockname path | **HONDA CONFIRMED** |
| Value type | signed 64-bit numeric inserted through `CFDictionarySetInt64` | **HONDA CONFIRMED** |
| Caller | `AirPlayReceiverSessionSetup` (`0x2854e0`) | **HONDA CONFIRMED** |
| Nested location | stream entry appended under response key `streams` | **HONDA CONFIRMED** |
| Meaning as phone-facing stream data port | likely intended by SETUP response structure; final serializer/write edge missing | **HIGH CONFIDENCE**, not wire-confirmed |
| Primary port serialized to phone | callback receives response dictionary; encoder/network write not mapped | **UNKNOWN** |

The separate listener in `AirPlayReceiverSessionSetup` at `0x2856fe` stores its port at session `+0x2b8`, inserts it into a different local dictionary using an opaque key at `0x285716`, and later uses that dictionary in setup/session control. Do not conflate this listener with the Type-110 stream's explicit `dataPort` entry inserted at `0x286160`.

## ClarityLink implication

Honda's structure demonstrates a response dictionary containing a `streams` array of per-stream dictionaries, each able to carry a numeric `type` and `dataPort`. That is structural evidence for multiple **stream response entries**, not proof that adding Type 111 is accepted or that a display descriptor can be appended. The future secondary listener can conceptually have its own port, but Honda's dispatch and iPhone behavior remain unverified. No second port is opened in this milestone.
