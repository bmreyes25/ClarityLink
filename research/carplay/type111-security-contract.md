# Type-111 security contract — Step 38

## Honda Type-110 derivation, recovered from jmcs

`AirPlayReceiverSessionSetup` reads `streamConnectionID` with `CFDictionaryGetInt64` in the Type-110 branch and rejects zero. It passes the receiver-session master material at `session+0x1b8` (length 16), the ID, and two 16-byte output buffers to `AirPlay_DeriveAESKeySHA512ForScreen` (`0x288d18`). The helper installs neither state nor sockets itself; Setup passes key/IV to `AirPlayReceiverSessionScreen_SetSecurityInfo` (`0x287d28`). That setter initializes AES-CTR at screen object `+0xc8`, finalizing an existing context first. Setup zeroes both temporary 16-byte buffers after installation.

The screen-specific helper formats two salts using `ASPrintF` with exact format `%s%llu`:

- `AirPlayStreamKey` + unsigned decimal `streamConnectionID`
- `AirPlayStreamIV` + unsigned decimal `streamConnectionID`

It calls `AirPlay_DeriveAESKeySHA512` (`0x288c6c`) independently for each. That routine hashes `salt bytes || master material` with SHA-512 and copies the first 16 digest bytes into the respective output. Thus the ID representation is **unsigned decimal ASCII**, not raw uint64 bytes or hex. Output key and IV are each 16 bytes. Helper-created salt strings are securely zeroed and freed; caller temporary output buffers are zeroed after use.

Offline code is in `src/claritylink-negotiation/screen_kdf.py`; it has synthetic deterministic tests only. No real/session material is recorded or used.

## What is and is not established for Type 111

- Honda uses this derivation for Type 110. Its Type-111 invalid branch never enters the helper.
- MHI2's pinned implementation reads Type-111 `streamConnectionID`, uses its stock session's master material, calls the stock screen derivation helper, and creates a separate Type-111 receive crypto context.
- The exact Honda primitive and Type110 byte contract are recovered; Honda Type-111 compatibility remains **unknown**.
- A simultaneous Type-110 and Type-111 receiver must use separate independent CTR contexts. Reusing the stock screen object's `+0xc8` context would interleave/advance one stream's counter and corrupt both. The project should own its key/IV/context and never overwrite Honda Type-110 state.

## Secret handling

Use only in-memory material. Never persist or log master material, derived key, IV, or decrypted payload. Logs may include state transitions, generation, port, sizes, status and (only if privacy policy permits) the streamConnectionID. Wipe temporary salt and key/IV buffers after installing/initializing their owning crypto context. Clear project CTR and receiver state at teardown.
