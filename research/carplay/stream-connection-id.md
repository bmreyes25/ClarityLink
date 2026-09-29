# Honda `streamConnectionID` trace — Step 33

**Binary:** `extracted/system/system/bin/jmcs`, SHA-256 `cbc7ba881648fb8ffdfcc4c1100a028345c37134a2ae3b9dff7d76572851c232` (matches the same-acquisition vendor copy).

## Request extraction and crypto use

The inlined `_ScreenSetup` body (DWARF source `AirPlayReceiverSession.c:2144`) in `AirPlayReceiverSessionSetup` (`0x2854e0`) contains a DWARF local named `streamConnectionID`, type `uint64_t`. In the Type-110 branch:

| Address | Evidence |
|---|---|
| ELF file offset `0x3374d9` | Runtime string literal `streamConnectionID` in the exact `jmcs` image |
| `0x2860a8–0x2860b2` | `CFDictionaryGetInt64(requestStreamDesc, key, &err)` for the stream connection identifier, inside inlined `_ScreenSetup` / `AirPlayReceiverSessionSetup` |
| `0x2860b4–0x2860b6` | 64-bit return is preserved in `r2:r3` |
| `0x2860bc` | zero ID is rejected to the error/cleanup path |
| `0x2860c4–0x2860d2` | call `AirPlay_DeriveAESKeySHA512ForScreen` with master key at session `+0x1b8`, length 16, ID in `r2:r3`, and output key/IV buffers |
| `0x2860d6–0x2860de` | call `AirPlayReceiverSessionScreen_SetSecurityInfo` with derived key and IV |
| `0x286124` | create a TCP listening socket with requested port 0 |
| `0x28614a–0x286168` | construct and append response entry with type 110 and assigned `dataPort` |

The extraction is a typed integer dictionary read, not a string or UUID conversion. The literal `streamConnectionID` is present in the ELF constant/string data and the DWARF local name and 64-bit value flow agree. Type-110 dispatch reaches this code after calling `AirPlayReceiverSessionScreen_Setup` at `0x28609c`.

## `inScreenStreamConnectionID`

`AirPlay_DeriveAESKeySHA512ForScreen` (`0x288d18`) has a DWARF formal parameter named `inScreenStreamConnectionID`, type `uint64_t`. The Setup code passes the just-read `streamConnectionID` in that argument position. This proves a direct request-ID-to-screen-crypto function argument binding.

The name `inScreenStreamConnectionID` is a debug-info parameter name, not evidence by itself of a persistent field with that name. I did not establish that the request ID is copied into a long-lived session struct. `AirPlayReceiverSessionScreen_Setup` separately writes a 64-bit dictionary lookup result at screen object `+0x10`, but the lookup key has not been semantically tied to `streamConnectionID`; do not conflate these paths.

## Security role and limitations

The ID is an input to screen-specific AES key/IV derivation, so its security role is **confirmed**. The returned key and IV are passed to `SetSecurityInfo`; local temporary buffers are cleared after that call. This makes it unsafe to implement Type 111 by inventing or reusing a connection ID without establishing the required derivation and key state.

The per-stream branch then allocates a listener and appends `{type: 110, dataPort: Y}`. No `streamConnectionID` echo was observed in the response construction. The newly created listener/response are associated by this same branch, but the accept-side mapping from that listener to a persistent screen object was not fully re-traced in this milestone.

```text
SETUP stream dict --[uint64 streamConnectionID]--> _ScreenSetup local
       --> AirPlay_DeriveAESKeySHA512ForScreen(..., inScreenStreamConnectionID)
       --> SetSecurityInfo(key, IV)
```

`REQUEST_TO_SESSION_BINDING = PARTIAL`: request-to-crypto context is confirmed; persistent ID storage and a display UUID association are not.
