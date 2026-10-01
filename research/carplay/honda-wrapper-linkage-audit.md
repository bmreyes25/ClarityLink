# Honda wrapper linkage audit — Step 43M

Reference ELF: `extracted/system/system/bin/jmcs`, SHA-256 `cbc7ba881648fb8ffdfcc4c1100a028345c37134a2ae3b9dff7d76572851c232`.

`.dynsym` and `.symtab` are present. The serious candidate names below are absent from `nm -D`/`.dynsym`; `objdump -R` finds no matching dynamic relocation or `JUMP_SLOT`. Their observed callsites disassemble as immediate direct Thumb `BL` instructions to same-ELF `.text` definitions. There is no PLT/GOT route for these callsites to redirect via ordinary ELF interposition.

| Symbol | `.symtab` | `.dynsym` / relocation | Call encoding | Static class |
|---|---|---|---|---|
| `AirPlayReceiverSessionSetup` `0x2854e0` | global text symbol | absent; no candidate relocation | direct BL at `0x28af72`; one caller | `DIRECT_INTERNAL_CALL` |
| `CFObjectSetProperty` `0x2928d0` | global text symbol | absent; no candidate relocation | direct BLs; 11 callers | `DIRECT_INTERNAL_CALL` |
| `_requestSendPlistResponse` `0x289f60` | local text symbol | absent; no candidate relocation | direct BLs; 4 callers | `LOCAL_STATIC_FUNCTION` / `DIRECT_INTERNAL_CALL` |
| `CFPropertyListCreateData` `0x28e6fc` | global text symbol | absent; no candidate relocation | direct BLs; 2 callers | `DIRECT_INTERNAL_CALL` |
| `HTTPMessageSetBody` `0x29d01c` | global text symbol | absent; no candidate relocation | direct BLs; 4 callers | `DIRECT_INTERNAL_CALL` |
| `HTTPConnectionSendResponse` `0x29dbe4` | global text symbol | absent; no candidate relocation | direct BL at `0x28b790`; one caller | `DIRECT_INTERNAL_CALL` |

All candidate bodies/calls are Thumb in this binary. The ELF `.symtab` global/local status is not a runtime visibility guarantee. Because the direct calls are already resolved branch immediates, static symbol visibility does not yield a wrapper route. Android loader precedence and any process runtime patching remain `HONDA_UNKNOWN` and are not enabled here.

**Decision:** ordinary existing-function interposition is statically unavailable for the successful Setup call path. A function-prologue or exact-call-site redirect would be required. The narrowest site is the existing serializer call at `0x28afba`, rather than a process-wide property setter or global Setup API.
