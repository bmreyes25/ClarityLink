# Step 36 — prove Honda screen header, AES-CTR, and media handoff

**Date:** 2026-09-29
**Starting commit:** `334014495c28b24c386e3af05c977da62f8ed8be`
**Scope:** offline disassembly of identity-verified Honda `jmcs` plus pinned MHI2/xcertplay and public classic AirPlay references. No vehicle, ADB, ptrace, firmware patch, live hook, car Type-111, cluster rendering, or unrelated control-plane work. No real keys/captures included.

## Honda control-flow result

`AirPlayReceiverSessionScreen_ProcessFrames` (`0x287d8d`) uses `select` on the accepted socket and calls `NetSocket_ReadInternal` with both required length and read capacity set to `0x80`. ReadInternal accumulates short `recv()`s until all 128 bytes are available; this proves a fixed header boundary. The separate `memset(...,0,0x80)` in ProcessFrames initializes an `fd_set`, not a packet header.

Honda reads LE32 `body_size` from header +0 and uses that value directly for allocation and a second exact-length read. The type switch loads one byte from header +4. Header +8 is loaded as a 64-bit timestamp-like value and sent through the configured time-conversion callback; without a callback, the path uses UpTicks. Config type 1 additionally reads float32 values at +16 and +20 and converts them to CF double properties. Bytes +24..+127 remain uninterpreted in this path.

After body read and timestamp handling, if security is enabled, ProcessFrames calls `AES_CTR_Update(ctx=session+0xc8, input=body, length=header.body_size, output=body)`. Header is plaintext; body is decrypted in place. The same screen CTR state is initialized during SetSecurityInfo, updated over successive bodies, and finalized at session cleanup. Init copies the 16-byte IV and starts byte offset at zero. Update carries partial-block position and increments the counter in place across update calls. No per-header/per-message reset occurs.

Type byte behavior:

| Value | Honda action | Assessment |
|---:|---|---|
| 0 | body -> ScreenStreamProcessData with stream, bytes, length, converted timestamp | probable VideoFrame |
| 1 | header float properties updated; body -> CF data property | probable VideoConfig; avcC not proven |
| 2 | body dropped/loop continues | probable heartbeat |
| 3 | unrecognized/log path | not handled as ForceKeyFrame in this function |
| 4 | body dropped/continue | probable Ignore |
| 5 | body dropped/continue | probable KeepAliveWithBody |

## Media callback/result

Type 0 passes one decrypted message body into the generic callback. Honda `mc_ScreenStreamProcessData` parses the body using a per-stream record-length mode: 1-byte, 2-byte big-endian, or 4-byte big-endian lengths are present in code. Its conversion branch writes literal `00 00 00 01` prefixes before record data. It then sets media-buffer `data_size` to produced output bytes, copies timestamp to `mc_stream_buf.timestamp` at +16, and calls `mc_stream_push_data` to the linked sink interface's `process_data` slot (+0x14). The concrete sink, exact record-to-NAL/AU relation, keyframe semantics, and downstream decoder remain unknown. Type 1 does not go through this callback in the ProcessFrames callsite.

## Prior-art test

The [classic AirPlay stream packet reference](https://openairplay.github.io/airplay-spec/screen_mirroring/stream_packets.html) describes a 128-byte header with LE32 payload size at 0, 16-bit type at 4, 16-bit auxiliary field at 6, 8-byte NTP timestamp at 8, type 0 video, type 1 codec/avcC, type 2 heartbeat. Honda confirms 128 bytes, body-size offset/endianness, message low byte at +4, timestamp-like +8, and matching config/media branches 1/0. Honda only loads one discriminator byte (high type byte is unvalidated) and does not prove NTP encoding or avcC body structure. Therefore Honda is a strong match to the classic packet family with unresolved header tails/semantics, not byte-for-byte equivalence asserted beyond recovered fields.

Pinned [MHI2 MU1440 `STREAM111_PROTOCOL.md`](https://github.com/harman-f/mhi2_altscreen_carplay/blob/c2f811f1a5c84dae3a62f4cf9b4a9e65fc3f7b3c/docs/research/STREAM111_PROTOCOL.md) documents the same 128-byte family and its own type-111 receiver: type 1 `avcC`, type 0 AES-CTR body, AVCC NALs converted to Annex B. MHI2 is target-specific evidence. Pinned [xcertplay source](https://github.com/shilapi/xcertplay/tree/3753867f0dd0e5c03490b987fb9df49b8ac96472) confirms 110/111 stream setup/display mapping but did not supply Honda wire proof. The [carlink_linux capability note](https://github.com/lvalen91/carlink_linux/blob/main/docs/CARPLAY_CAPABILITIES.md) lists a newer opcode table 0..5 (including ForceKeyFrame=3); Honda's current ProcessFrames does not handle 3, so do not project that newer table onto Honda.

## Offline code decision

Implemented `ScreenFrameParser`: incremental 128-byte + LE32 body-size parser that preserves raw header/body and unknown opcodes; a configurable local body safety limit is explicitly not a protocol limit. Implemented `ScreenCryptoModel`: injected AES block function and continuous CTR counter/partial block model, with no key derivation or real key material. Tests use a toy block-function double solely for CTR state continuity; they do not claim to verify AES or captured Honda traffic. No avcC parser, H.264 access-unit extractor, listener, Type-111 Setup, or real AES provider was added.

## Decision gate

```text
HONDA HEADER SIZE: 128 bytes, confirmed by exact required read followed by offset-specific header parsing
PAYLOAD LENGTH FIELD: LE32 at +0; direct allocation and exact body read; excludes the 128-byte header
MESSAGE TYPE FIELD: byte at +4; switch values 0,1,2,5,4; high byte +5 not checked
HEADER ENCRYPTED: NO
BODY ENCRYPTED: YES when screen-session security flag is set; body-only in-place AES-CTR
AES CTR STATE MODEL: continuous over encrypted message bodies; partial keystream offset/counter retained; reinitialized on security install, finalized at cleanup
TIMESTAMP FIELD: LE64 at +8 passed to session converter; likely NTP-family match, exact Honda encoding UNKNOWN
HONDA OPCODES: 0 media callback; 1 config-property body; 2/4/5 ignored/released; 3/other unrecognized
VIDEOCONFIG OPCODE: 1 (probable semantic match from separate config property path)
VIDEOCONFIG FORMAT: UNKNOWN; public/prior-art avcC is a strong hypothesis only
SPS/PPS TRANSFORM: no extraction proven; type-1 body passed as CF data; type-0 callback writes Annex-B start codes in conversion path
VIDEO WIRE FORMAT: type-0 callback sees mode-selected 1/2/4-byte length-delimited records; exact stream mode/AU semantics unresolved
ANNEX-B SYNTHESIS: CONFIRMED, literal 00 00 00 01 before converted record data
ACCESS UNIT BOUNDARY: one type-0 message is one callback/push invocation; whether payload is exactly one complete AU UNKNOWN
MC_SCREENSTREAMPROCESSDATA INPUT: type-0 decrypted body pointer+length, stream object, converted timestamp, zero trailing metadata; callback builds a length-record-transformed media buffer and timestamp
TYPE111 HEADER REUSE: YES as a classic ScreenStream family parser candidate; Honda Type-111 acceptance remains unproven
TYPE111 CRYPTO REUSE: UNKNOWN for Honda; MHI2 demonstrates same derivation/CTR model on its target
OFFLINE HEADER PARSER READY: YES (fixed header/body splitter only)
OFFLINE VIDEOCONFIG PARSER READY: NO
OFFLINE H264 EXTRACTOR READY: NO
OFFLINE CRYPTO READY: YES for CTR state model with an injected AES block provider; self-contained AES provider/key derivation not included
EXECUTABLE TYPE111 RECEIVER READY: NO
LIVE TEST READY: NO
BIGGEST BLOCKER: Honda's type-1 body is not proven avcC and the per-stream length-record mode is not tied to complete H.264 access-unit semantics
```

## Deliverables and verification

Added `research/carplay/honda-screen-header.md`, `honda-screen-crypto.md`, `mc-screenstream-input.md`; updated read-loop, framing, VideoConfig, H.264, Type-111 model, transport/presentation, state/index/next-action notes. Added `src/claritylink-transport/` header parser and CTR state model plus synthetic offline tests. No vehicle/live actions or real keys. Relevant tests and `git diff --check` are run before commit.
