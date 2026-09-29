# AltScreen transport and presentation are separate planes

**Step 36 update, 2026-09-29.** Honda ELF evidence is authoritative for Honda; public classic AirPlay and pinned MHI2 are comparison evidence.

## Transport / media security

```text
SETUP Type-110 streamConnectionID
 -> receiver session key material + ID -> per-screen key/IV
 -> listener -> accepted per-thread NetSocket
 -> exact 128-byte plaintext header
 -> LE32 body size at +0, discriminator byte at +4
 -> read body exactly, AES-CTR decrypt in place if security is enabled
 -> type 0 timestamped ScreenStreamProcessData
 -> mc_ScreenStreamProcessData record parser -> transformed media buffer -> sink
```

Step 36 proves Honda's fixed header and length boundary by control flow, not merely by the 128-byte read constant. It also recovers body-only AES-CTR with a persistent stream context and message branches 0/1/2/4/5. Type 0 is a probable VideoFrame; type 1 is a probable config branch passed as CF data; 2/4/5 are skipped; 3 is unrecognized in this function. Type-1 body format, full type semantics, and complete AU/sink contract remain partly unknown. The callback's length-mode parser and Annex-B prefix synthesis are documented separately.

## Presentation / UI ownership

```text
/info display descriptor and UUID -> phone display/UI selection
 -> suggestUI/showUI/stopUI/ViewArea control -> presentation ownership
```

No direct UUID-to-stream crypto binding has been found. Honda PlatformControl/SessionControl symbols exist while exact command semantics remain unknown. MHI2 keeps transport and UI operations separate on its target; Honda ordering remains unknown.

## Type-111 consequence

The screen header/framing parser can be reused as a family candidate for a future ClarityLink Type-111 stream, since Honda Type-110 now matches the classic 128-byte body-length/discriminator structure and MHI2 Type-111 uses the legacy ScreenStream family. Honda Type-111 negotiation/crypto acceptance remains unproven. The offline parser and CTR state model preserve this boundary; neither is a complete receiver or H.264 decoder. See `honda-screen-header.md`, `honda-screen-crypto.md`, `mc-screenstream-input.md`, and `type111-transport-model.md`.
