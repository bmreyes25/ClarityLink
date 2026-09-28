# Screen setup input trace

**Status: dictionary lookup family confirmed; schema/key semantics remain unresolved.**

## Caller and data flow

`AirPlayReceiverSessionSetup` (`jmcs` VA `0x2854e0`, Thumb symbol `0x2854e1`) directly calls `AirPlayReceiverSessionScreen_Setup` (`0x287d5c`, Thumb symbol `0x287d5d`) at call site `0x28609c`. The callee receives the screen object in `r0` and a lookup object in `r1`. It passes the lookup object, a literal-derived key-object pointer, and a stack error/status slot to `0x294598`. It stores the two returned registers at screen-object offsets `+0x10` and `+0x14`. If the status slot is nonzero, it stores `0x46` and `0` instead. The function returns zero.

## Helper classification

`0x294598` calls `0x28e520`, which calls the local `CFLDictionaryGetValue` implementation at `0x28f37c`. That implementation performs `__CFLDictionaryFindKey` and obtains the dictionary value. On success `0x294598` tail-calls `0x293d40` to convert/return the value; on failure it writes an error/default marker and returns zero in both registers. Thus the helper family is a Honda `CFLDictionaryGetValue` lookup plus typed conversion, not proven CoreFoundation, plist, or raw struct-offset access.

The literal-derived key is an object pointer in the local CFL constant pool; no stable human-readable key string was recovered from the indexed string listing. Do not assign a semantic label from the value `0x46` or the key pointer alone.

| Source | Destination | Observed type/data | Later consumers | Confidence |
|---|---|---|---|---|
| CFL dictionary lookup result via `0x294598` | screen object `+0x10` | first returned word; numeric meaning not established | screen/session code; semantic xrefs not yet bounded | High data flow; unknown meaning |
| CFL dictionary lookup result via `0x294598` | screen object `+0x14` | second returned word | passed as screen-object pointer in caller setup flow; precise consumers require object-layout cross-reference audit | High data flow; unknown meaning |
| lookup status at callee stack output slot | fallback to `+0x10/+0x14` | `0x46`, `0` | error/default path | High |

**Input object type:** CFL dictionary compatible, high confidence from implementation. **Key/field:** unresolved. **Return:** converted pair in `r0/r1`; exact scalar/compound semantic type unresolved. No guessed width/height/ID/port labels are introduced.
