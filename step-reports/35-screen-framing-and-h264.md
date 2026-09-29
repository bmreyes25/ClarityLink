# Step 35 — screen decrypt, VideoConfig, and H.264 framing

**Date:** 2026-09-29
**Starting commit:** `ab5096edbc6d922cdb45d2dca2eaba6d924c674e`
**Scope:** offline static analysis of identity-verified Honda `jmcs` and pinned MHI2/xcertplay source. No vehicle, ADB, ptrace, firmware patch, live hook, Type-111 implementation on the car, cluster rendering, or registry work. No tests were added or run because no implementation was justified.

## Recovered chain and limits

Honda accepted-socket path is `_ScreenThread` -> `SocketAccept` -> `NetSocket_CreateWithNative` -> `AirPlayReceiverSessionScreen_ProcessFrames` -> `NetSocket_ReadInternal` -> `recv`. Accepted fd is held at NetSocket +4; method slot +0x14 reads into screen-session buffer +0x48 with an initial maximum request of 128 bytes. The 10-second timeout applies to listener accept; the saved evidence does not establish a read timeout or reconnect loop.

Type-110 setup derives 16-byte screen key and IV from 16-byte session master material plus nonzero uint64 `streamConnectionID`, then installs screen security. Honda's screen receive cipher is AES-CTR (`AES_CTR_Update`); `AES_CBCFrame_Init` is a different MHI2 security-observation seam. AES-CTR context is initialized at screen security install and finalized at stop. Per-message IV reset, counter framing, and exact decrypt boundaries are not recovered sufficiently for a standalone implementation.

After decrypt, `ScreenStreamProcessData` dispatches the callback to Honda `mc_ScreenStreamProcessData` (`0xbee91`), with stream/context, data pointer, and length in `r0/r1/r2`. That callback parses length-prefixed records with multiple branch-dependent widths/byte orders and synthesizes four-byte start-code-like prefixes in some branches. It allocates/pushes a media buffer through `mc_stream_alloc_buf` and `mc_stream_push_data`; the sink method at interface +0x14 is `process_data`. The callback-to-concrete-sink/decoder edge, byte content and size for an identified H.264 AU, timestamp source, VideoConfig discriminator/body, and keyframe semantics remain unknown.

## Prior art

At pinned MHI2 commit `c2f811f1a5c84dae3a62f4cf9b4a9e65fc3f7b3c`, `docs/research/STREAM111_PROTOCOL.md` documents a MU1440-specific 128-byte ScreenStream header with LE uint32 body size at offset 0 and opcode at offset 4, `avcC` VideoConfig, encrypted AES-CTR VideoFrame body, AVCC NAL length-prefix payload, and Annex-B conversion. Its native receiver parses SPS/PPS and NAL width and recognizes IDR NAL type 5. xcertplay is a useful display/stream setup prior-art receiver, but the checked source did not provide Honda framing evidence. These details are not promoted to Honda claims.

## Implementation decision

No `src/claritylink-transport/` code or `tests/transport/` were created. A parser based on the MU1440 framing note would hard-code unsupported Honda assumptions; synthetic tests would validate those assumptions, not Honda compatibility. Crypto derivation inputs are known, but AES state progression and Honda update/frame boundary are not yet precise enough for a standalone testable transport crypto abstraction.

```text
SOCKET READ LOOP: NetSocket_ReadInternal -> recv; accepted fd in per-thread NetSocket +4; buffer session +0x48; max initial request 128; short reads handled; accept timeout 10 s; EOF/read timeout/reconnect semantics partial/unknown
DECRYPT FUNCTION: AES_CTR_Update in ProcessFrames before ScreenStreamProcessData; exact per-message boundaries/arguments need focused confirmation
AES MODEL: session master material (16 B) + streamConnectionID (u64) -> derived key/IV; CTR state init at security install, update while receiving, finalize at stop; reset/counter details unknown
FRAME HEADER: Honda unknown; MHI2 prior art only: 128 B, LE body size @0, opcode @4
FRAME BOUNDARY: Honda unknown
MESSAGE TYPES: Honda values/handlers unknown
VIDEOCONFIG: Honda structure/discriminator unknown; MHI2 prior art uses avcC with SPS/PPS/NAL length size
H264 FORMAT: Honda unknown; MHI2 prior art uses decrypted AVCC length-prefixed AUs then Annex-B conversion
KEYFRAME: Honda unknown; MHI2 prior art checks IDR NAL type 5
PROCESS_DATA INPUT: stream/context-like object + data pointer + length; downstream media buffer is created/pushed, but exact H.264 content/size/timestamp unknown
TYPE111 FRAMING REUSE: UNKNOWN
TYPE111 CRYPTO REUSE: UNKNOWN for Honda (MHI2 demonstrates reuse on its target)
OFFLINE PARSER READY: NO
OFFLINE CRYPTO MODEL READY: NO
OFFLINE TYPE111 TRANSPORT READY: NO
LIVE TRANSPORT TEST READY: NO
BIGGEST BLOCKER: exact Honda plaintext screen-message boundary/header and VideoConfig discriminator/body have not been recovered
```

## Deliverables

Added/updated `research/carplay/honda-screen-read-loop.md`, `screen-crypto.md`, `honda-screen-framing.md`, `honda-video-config.md`, `honda-h264-format.md`, `type111-transport-model.md`, and `transport-vs-presentation.md`. State/index/next-action updated. No code/tests were warranted. Offline `git diff --check` required before handoff.
