# Step 37 — close the Honda media pipeline and prepare Type111 implementation

**Date:** 2026-09-29
**Starting commit:** `10c16e9`
**Scope:** offline static analysis of the identity-verified Honda `jmcs` ELF; synthetic-only parser/CTR tests. No vehicle, ADB, ptrace, patching, live hook, or live Type111 work.

## Evidence identity

Honda binary SHA-256: `cbc7ba881648fb8ffdfcc4c1100a028345c37134a2ae3b9dff7d76572851c232`. Screen path disassembled around `0x287d8d`, `mc_ScreenStreamSetProperty` at `0xbe6fc`, `mc_ScreenStreamProcessData` at `0xbee90`, and `H264ConvertAVCCtoAnnexBHeader` at `0x29f28c`. Saved exact disassembly commands/claims are tied to this binary, not public protocol assumptions.

## Breakthrough: config selector is the media parser selector

```text
ProcessFrames opcode 1 at 0x2880a8
  -> CFObjectSetPropertyData at 0x288120 (nonempty body)
  -> ScreenStream property callback
  -> mc_ScreenStreamSetProperty at 0xbe6fc
  -> H264ConvertAVCCtoAnnexBHeader at 0xbe7b4 / 0xbe7ee
  -> derived `(data[4] & 3) + 1` stored at callback context +0x14

ProcessFrames opcode 0 at 0x2880a2
  -> ScreenStreamProcessData
  -> mc_ScreenStreamProcessData at 0xbee90
  -> reads the same callback-context +0x14
  -> parses length-prefixed records, writes Annex-B prefixes, pushes one buffer
```

Honda's helper directly establishes avcC-like structure: byte 4 low two bits give length-size-minus-one; byte 5 low five bits give SPS count; SPS/PPS sizes are BE16; SPS/PPS are copied and each receives a literal `00 00 00 01` prefix. It does not validate configurationVersion/profile/compatibility/level. The best classification is **AVCC-LIKE, HONDA HIGH CONFIDENCE**, rather than claiming strict spec validation.

`mc_ScreenStreamSetProperty` stores converted parameter sets at callback context `+0x08`, byte size at `+0x0c`, and the derived record width at `+0x14`; it resets one-shot flag `+0x10`. On the next normal type-0 conversion, `mc_ScreenStreamProcessData` copies the stored config prefix into the output buffer and sets `+0x10`. Thus the first media buffer after each config update receives Annex-B SPS/PPS before frame records. A later type-1 config replaces the prior converted config and width and resets the prepend flag. No explicit decoder flush or generation counter was found in this setter.

## Callback record and output behavior

Supported callback selector values are 1, 2, and 4. Width 2 and width 4 are assembled big-endian; width 1 is a byte. avcC can derive width 3, but the media callback has no width-3 parser branch. All records in the message are processed by a cursor loop; the normal conversion path allocates an expanded buffer, groups records into one `mc_stream_buf`, stores produced byte count at +8, copies timestamp at +16, and invokes `mc_stream_push_data` once at `0xbf2fe`.

Honda's loop includes additional zero-run normalization at `0xbf294`–`0xbf40e`; the literal prefix and record grouping are proven, but the normalization's complete payload semantics are unresolved. ClarityLink's `H264Extractor` performs safe width/bounds checking and canonical start-code insertion for synthetic input, but cannot yet claim byte-exact behavior for every Honda record. A message maps to one media buffer; calling it exactly one H.264 access unit is high-confidence, not Honda's explicit term.

There is a second callback mode: context byte `+0x11 != 0` makes Honda copy the whole opcode-0 body unchanged to a media buffer, bypassing both the +0x14 length-width parser and the one-time SPS/PPS prefix. The effective Type110 value for +0x11 has not been recovered. The offline core exposes this as explicit `direct_body_mode`; normal record conversion is not asserted as the only Honda mode.

## Config and header inputs

| Input | Source | Honda handling | Finding |
|---|---|---|---|
| Body length | Header +0 LE32 | allocation/exact read; decrypted before dispatch if security flag set | Honda-confirmed |
| Opcode | Header +4 byte | `0` media, `1` properties/config, `2/4/5` drop/continue, `3/other` unknown log path | Honda-confirmed actions; semantic labels except media/config are probable |
| Timestamp-like value | Header +8 LE64 | callback conversion at session +0x20 when enabled, else UpTicks; passed to type0 callback | NTP interpretation UNKNOWN |
| Config float A | Header +16 binary32 | converted to CF double property | consumer meaning UNKNOWN |
| Config float B | Header +20 binary32 | converted to CF double property | consumer meaning UNKNOWN |
| Config bytes | opcode1 body, when nonempty | `CFDataGetBytePtr/Length`, AVCC-to-Annex-B helper | AVCC-like high confidence |
| avcC prefix byte 4 | config +4 | low 2 bits + 1 -> selector at context +0x14 | Honda-confirmed |
| SPS count | config +5 | low 5 bits | Honda-confirmed |
| PPS count | after SPS records | byte count, if any data remains | Honda-confirmed; helper accepts exact end after SPS as no-PPS case |

Trailing config bytes after parsed PPS are not included in Honda's converted output. Profile fields are not semantically parsed. SPS/PPS are copied as opaque byte arrays without NAL type checks. A zero-body type-1 message updates its two float properties but does not invoke the CFData property callback.

## Crypto by opcode

The body-only `AES_CTR_Update` is before the opcode switch. If screen security is enabled, every message body's declared bytes are decrypted in place and advance the same CTR context, including type 1 config and handled/dropped opcodes 2/4/5. If security is off, no CTR call occurs. Zero-length bodies consume zero bytes. Header remains plaintext. Therefore encrypted type-1 config advances CTR before the following type-0 frame. The session context is not reset per message.

## Timestamp, media sink, and keyframe status

Header +8's LE64 value is passed through a per-session function pointer or replaced by UpTicks. Exact converter and wire timebase remain unknown. The output timestamp is copied to `mc_stream_buf.timestamp`. An Android MediaCodec backend exists and divides media-buffer timestamps by 1000 before `queueInputBuffer`, but no registration/call edge proves it is the active sink for this CarPlay stream. `mc_stream_push_data` reaches the linked `mc_stream_sink_ifc.process_data` slot (+0x14); concrete active sink remains unknown. No NAL type / IDR / sync-frame flag logic was found in this ScreenStream callback/config layer.

## Honda Setup correction and Step 38 preparation

`AirPlayReceiverSessionSetup` (`0x2854e0`) iterates `streams[]`; type is loaded at `0x28590e`. Type111 has no handler and reaches the unknown-type logging block at `0x2861f6`, but the loop then advances and continues at `0x286220`. This proves no Type111 setup case; it does **not** prove immediate transaction failure. Type110 creates its listener (`ServerSocketOpen` call `0x286124`), inserts `dataPort` (`0x286160`), and appends the response with `_AddResponseStream` (`0x284db8`). `_ScreenTearDown` (`0x284628`) and `AirPlayReceiverSessionTearDown` (`0x2852ec`) are relevant failure paths. Exact Type111-only/mixed response and partial rollback remain Step 38 tasks.

## Offline implementation

Added:

- `video_config.py`: bounded AVC configuration parser for fields Honda reads; opaque trailing bytes preserved.
- `h264_extractor.py`: safe 1/2/4-byte record parser and Annex-B start-code emission; width 3 rejected.
- `receiver_core.py`: incremental framing + optional shared CTR + config state + video/control/unknown events; config prepended once after each config.
- `tests/transport/test_media_pipeline.py`: synthetic config, multi-NAL, malformed lengths, config update, timestamp retention, split/multiple ScreenStream messages, CTR continuity across config, and reset tests.

The code uses no key material, captured traffic, socket, rendering API, or real AES implementation. It relies on the existing injected `ScreenCryptoModel`; synthetic CTR tests use a toy block function, not AES validation.

## Prior-art comparison (after Honda analysis)

| Concept | Honda Type110 | Classic AirPlay / MHI2 Type111 | Assessment |
|---|---|---|---|
| Header | 128 bytes; LE32 body length +0, byte opcode +4 | classic packet docs describe same field family; pinned MHI2 Type111 docs 128-byte family | match for recovered fields; Honda authoritative |
| Type 1 config | Honda `H264ConvertAVCCtoAnnexBHeader`; byte4 width, byte5 SPS count, BE16 SPS/PPS | classic docs and MHI2 describe avcC | Honda AVCC-like path confirmed; prior art corroborates |
| Type 0 video | selector-linked width 1/2/4, output Annex-B records | MHI2 reports length-prefixed H.264 and Annex-B conversion | likely compatible family; byte-normalization and AU semantics remain |
| CTR | continuous body-only Honda Type110 | MHI2 Type111 reports AES-CTR | Honda Type111 reuse unknown |
| Timestamp/AU/keyframe | converter-based timestamp; AU semantics high-confidence; keyframe logic absent | prior art may label NTP/frame opcodes | don't project semantics onto Honda |

Pinned source evidence is recorded in the existing Step 36 report and links: [classic AirPlay ScreenStream packet note](https://openairplay.github.io/airplay-spec/screen_mirroring/stream_packets.html), [MHI2 `STREAM111_PROTOCOL.md` at `c2f811f`](https://github.com/harman-f/mhi2_altscreen_carplay/blob/c2f811f1a5c84dae3a62f4cf9b4a9e65fc3f7b3c/docs/research/STREAM111_PROTOCOL.md), [xcertplay pinned tree](https://github.com/shilapi/xcertplay/tree/3753867f0dd0e5c03490b987fb9df49b8ac96472), and current [carlink Linux capability note](https://github.com/lvalen91/carlink_linux/blob/main/docs/CARPLAY_CAPABILITIES.md). They remain prior-art/comparison, not Honda proof.

## Readiness gate

| Component | Status |
|---|---|
| Header parser | READY |
| CTR state model | READY with injected AES primitive; not AES KAT verified |
| Screen-key derivation model | NOT READY as executable code |
| VideoConfig parser | READY for Honda-consumed avcC-like SPS/PPS subset |
| H.264 extractor | READY for safe length framing; not yet byte-exact for Honda zero-run normalization |
| Type110 offline receiver core | READY for synthetic/injected-crypto model; not live-compatible proof |
| Type111 request model | NOT READY |
| Type111 Setup handler | NOT READY |
| Type111 crypto integration | NOT READY |
| Live interposer | NOT READY |
| Cluster renderer | NOT READY in this media milestone |
| Presentation control | NOT READY |

## Verification and next action

`python3 -m unittest discover -s tests/transport -v`: **29 passed**. `git diff --check`: pass before final stage.
**Media blocker:** decode the extra zero-run transformation in `mc_ScreenStreamProcessData` (`0xbf294`–`0xbf40e`) and prove full timestamp conversion.
**Type111 blocker:** resolve request/security inputs and mixed-entry response/rollback semantics.
**Next:** Step 38 offline Type111 SETUP/security contract using `research/carplay/type111-step38-contract.md`.
