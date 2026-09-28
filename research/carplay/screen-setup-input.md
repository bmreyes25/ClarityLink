# Screen setup input trace

**Status: partial.** Offline trace of the indexed MY16ADA `jmcs` focused disassembly and the local ignored binary. No protocol bytes or live session were used.

## Caller and arguments

| Item | Finding | Confidence |
|---|---|---|
| Setup | `AirPlayReceiverSessionScreen_Setup`, VA `0x287d5d` | High |
| Direct caller | `AirPlayReceiverSessionSetup`, VA `0x2854e1`; direct call at `0x28609c` | High; targeted linear call scan of indexed `jmcs` |
| Setup arg 0 | Receiver screen-session pointer, retained in `r4`; writes two values at offsets `+0x10` and `+0x14` | High for ABI/register and stores; field semantics unknown |
| Setup arg 1 | Pointer passed to helper `0x294598` as lookup object | High for data flow; concrete type unknown |
| Setup return | Constant zero | High |
| Caller class | Receiver setup routine; whether it is reached from a request parser, event, or another internal state transition remains unknown | Partial |

`Setup` passes arg 1 to `0x294598` with a key pointer derived from an address literal and an output slot at its stack `+4`. The helper returns two register values, stored at receiver offsets `+0x10/+0x14`; if the output slot is nonzero, those fields are replaced with `0x46` and zero. Key text, value types, and semantic names are not recovered in the available annotated excerpt, so fields remain unnamed.

## Request schema ledger

| FIELD / KEY | TYPE | SOURCE | PRIMARY VALUE IF KNOWN | USED BY | CONFIDENCE |
|---|---|---|---|---|---|
| lookup key at Setup literal-derived address | Unknown | `AirPlayReceiverSessionScreen_Setup` -> helper `0x294598` | Unknown | Result stored at receiver `+0x10` | Low; key bytes not decoded |
| second helper return | Unknown | Helper `0x294598` | Unknown | Stored at receiver `+0x14`, except error/default path writes zero | Medium for data flow only |
| helper status/output slot | Stack output at Setup `sp+4` | Helper `0x294598` | If nonzero, defaults receiver fields to `0x46`, `0` | Setup branch | High for control flow; meaning unknown |

## Boundary and missing evidence

No external transport or parser is established. The exact missing artifact is a complete caller/xref and control-flow trace above `AirPlayReceiverSessionSetup` within `jmcs`, including its entry arguments and the producer of the screen-session event. The indexed focused analysis does not include that trace or the event producer.

No `CFDictionary`, plist, HTTP dictionary, or other concrete object class is claimed. `0x294598` is only established as a key-and-output style helper by its call shape; its implementation/type contract is not included in the bounded trace.
