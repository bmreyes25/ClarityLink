# AltScreen transport and presentation are separate planes

**Step 37 update, 2026-09-29.** Honda ELF evidence is authoritative for Honda; public classic AirPlay and pinned MHI2 are comparison evidence.

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

Steps 36–37 prove Honda's fixed header, length boundary, and body-only AES-CTR with a persistent stream context. Opcode 0 sends one decrypted body to the media callback; opcode 1's CFData callback parses an avcC-like SPS/PPS array, derives `(byte4 & 3)+1`, stores width at per-stream context `+0x14`, and stores converted config for one-time prefixing on a later opcode-0 media buffer. Widths 1/2/4 are handled by the normal callback path; width 3 is derived but has no parser branch. Callback context `+0x11` selects an alternate direct-body path whose active value remains unknown. Zero-run normalization and timestamp units remain unresolved. The offline synthetic Type110 receiver core is implemented with explicit mode and injected crypto inputs; it is not a live Type111 receiver.

## Presentation / UI ownership

```text
/info display descriptor and UUID -> phone display/UI selection
 -> suggestUI/showUI/stopUI/ViewArea control -> presentation ownership
```

No direct UUID-to-stream crypto binding has been found. Honda PlatformControl/SessionControl symbols exist while exact command semantics remain unknown. MHI2 keeps transport and UI operations separate on its target; Honda ordering remains unknown.

## Type-111 consequence

The header/config/media components are a strong family-reuse candidate for future ClarityLink Type 111, since Honda Type110 and MHI2 Type111 use the legacy ScreenStream family. Honda Type111 crypto, Setup, and acceptance remain unproven. The Type110-compatible offline core exists, but not key derivation, a production AES provider, decoder integration, or live listener. See `honda-screen-header.md`, `honda-screen-crypto.md`, `honda-video-config.md`, `honda-h264-format.md`, `mc-screenstream-input.md`, and `type111-transport-model.md`.
