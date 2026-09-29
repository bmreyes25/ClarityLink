# Honda stock-delegating hook ABI assessment

## Candidates

| Candidate | Stock first? | Primary behavior | Append ability | Risk / verdict |
|---|---|---|---|---|
| A. `AirPlayReceiverSessionSetup` entry (`0x2854e0`) | yes, by calling original | Can preserve stock status and output if wrapper is transparent | Could alter output only after original if output pointer and ownership are understood | **High risk now**: exact signature, out-object ownership, reentrancy and callback timing incomplete |
| B. immediately after original returns | yes | Best conceptual preservation point | Output pointer likely contains response dictionary, but full parameter mapping/ownership missing | **Promising, not safe yet** |
| C. `CopyDisplaysInfo` builder (`0x287ae0`) | yes, call original first | Main-only dictionary remains intact | No multi-display collection evidenced; this is not the SETUP stream array | **Poor fit** |
| D. `_AddResponseStream` (`0x284db8`) | invoked by stock builder | Existing stream append behavior retained | Natural stream-entry location; but adding second response without second request semantics is unproven | **Potential smallest structural hook**; ABI of internal helper and request eligibility need recovery |
| E. generic serializer pre-call | unknown | Could preserve fields if actual object is setup response | Session response serializer not identified | **Not currently targetable** |

## Function ABI currently known

`AirPlayReceiverSessionSetup` is an ARM EABI/Thumb function returning `OSStatus` in `r0`. Entry disassembly saves `r0` as session, `r1` as request dictionary, and stores `r2` as an output pointer at `[sp+0x50]`; the function writes the response dictionary through that pointer at `0x286260`. It later invokes a completion callback indirectly at `0x2862b0` with status/context; this callback is not passed the response dictionary. DWARF has the function return type and source line but no formal parameter DIEs in this ELF, so the complete parameter declaration and ownership semantics remain **UNKNOWN**.

The response dictionary is released on local failure/cleanup paths; its lifetime when published to the caller and passed to the callback is not fully established. Setup builds it as mutable. `CFDictionarySetValue` and `_AddResponseStream` retain/copy behavior follows Honda's CF implementation conventions, but hook-safe retain/release at the callback boundary is **UNKNOWN**.

```text
HOOK TARGET: none approved from static evidence
BEST FUTURE INVESTIGATION TARGET: post-Setup response out-parameter/callback boundary, once caller and ownership are mapped
CALLING CONVENTION: ARM EABI AAPCS32 (Thumb); exact formal signature incomplete
RETURN: OSStatus in r0
THREAD CONTEXT: unknown
ERROR SEMANTICS: status codes and error-output path exist; complete interposer semantics unknown
SAFE TO APPEND: UNKNOWN
```

## Minimal hook-surface conclusion

The response already has `streams: CFArray` and per-entry `type`/`dataPort` fields. This is the strongest potential extension boundary. The safest conceptual shape remains “call stock, preserve the original object and its primary stream entry, then add a separate ClarityLink entry before the proven serializer.” However, no serializer relation, callback ownership guarantee, iPhone acceptance behavior, secondary descriptor construction, or Type-111 handling is established. Therefore the proposed hook is **not yet proven feasible** and no hook is implemented.
