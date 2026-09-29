# Honda Type-110 screen framing — Step 36

**Binary:** identity-verified Honda `jmcs` at `research/carplay/jmcs-acquisition-identity.md`. Offline static analysis only.

## ProcessFrames state machine

```text
initialize local select fd_set (memset 0x80 bytes; not protocol)
loop:
  select accepted native socket fd
  if readable:
    NetSocket_ReadInternal(min=128, capacity=128, dst=session+0x48)
      accumulate partial recv results until exactly 128 header bytes
    body_len = LE32(session+0x48[0..3])
    message_type = session+0x48[4]
    if body_len != 0:
      allocate body_len bytes
      NetSocket_ReadInternal(min=body_len, capacity=body_len, dst=allocation)
        accumulate partial recv results until body_len bytes
    derive media timestamp from LE64 header bytes +8 via session converter
      (fallback uses local UpTicks when converter is absent)
    if screen security flag session+0x1e4 is set:
      AES_CTR_Update(ctx=session+0xc8, input=body, length=body_len, output=body)
    switch message_type:
      0 -> ScreenStreamProcessData(stream, body, body_len, timestamp, zero flags)
      1 -> update config-related session properties; pass body bytes as CF data property
      2, 4, 5 -> no media/config dispatch; release body and continue
      other (including 3) -> log/unrecognized path; release/return status
  separate scheduled/control wake path can recv up to 64 bytes and handles
  leading bytes 'q', 's', 'f'; it is not the screen packet header parser
```

The selected descriptor is stored on the per-thread NetSocket at +4. `NetSocket_ReadInternal` (`0x2a0055`) retries positive partial reads and continues until its minimum requested count is met. EOF before that count returns a read error; no reconnect loop appears here. The receive path's `0x80` literal at `0x287eec` sets the 128-byte exact header request, followed by the reader call at `0x287f04`. The other `0x80` use at `0x287dda` is the `fd_set` memset size. There is no evidence that the memset size is a header field.

## Exact fields/branches

| Offset | Width | Use |
|---:|---:|---|
| `+0` | 4 bytes, LE32 | body length; direct `malloc` and exact second read |
| `+4` | 1 byte | dispatch discriminator |
| `+5` | 1 byte | no proven use in ProcessFrames switch |
| `+6` | byte; bit 1 | type-1 path stores bit 1 into session state, which gates the timestamp-conversion callback on subsequent messages; remaining semantics unknown |
| `+7` | 1 byte | no proven use |
| `+8` | 8 bytes, LE64 | passed to time conversion callback, or ignored in favor of UpTicks fallback |
| `+16` / `+20` | 4 bytes each, binary32 | only read by type-1 config path and converted to CF double properties; property meanings unknown |
| `+24..+127` | opaque | no established use in this function |

### Honda type switch

| Value | Exact path in Honda | Semantics supported |
|---:|---|---|
| `0` | Decrypt body if screen crypto active, then call generic `ScreenStreamProcessData` at `0x2880a2` with stream `session+0x1ec`, body pointer, body length, converted timestamp, and zeroed trailing flags | **Probable match to AirPlay VideoFrame**; call path carries media bytes |
| `1` | Decrypt body if active; load header float fields at +16/+20; set two CF double properties; if body nonempty pass its bytes as a CF data property | **Probable match to VideoConfig**; Honda code does not parse avcC/SPS/PPS |
| `2` | No body/config dispatch; body is released; returns to loop | **Probable heartbeat match**, supported by empty-body-compatible handling, but Honda semantics are not explicitly named |
| `3` | Falls to unrecognized/log path | **Not handled as a ForceKeyFrame opcode here** |
| `4` | No dispatch, release/continue | **Probable Ignore match** |
| `5` | No dispatch, release/continue | **Probable KeepAliveWithBody match** |
| other | unrecognized/log path | Unknown |

This is a partial match to the public classic field positions and public opcode family. The code compares types 0,1,2,4,5, but not 3. Public CarPlay references may describe newer/different opcode sets; they are not substituted for this Honda switch.

## Complete frame rule

Honda's fixed header boundary is 128 bytes, established by an exact read target and subsequent loads from the buffer. The next body boundary is the unsigned LE32 field at offset zero; ProcessFrames requests exactly that many more bytes before decrypting or dispatching. This is a message = 128-byte header + `body_len` body rule. TCP segmentation does not define message boundaries: `NetSocket_ReadInternal` loops over short reads; back-to-back messages are consumed by repeated ProcessFrames loop iterations rather than inferred from recv packetization. Zero-length bodies skip allocation/read and proceed to dispatch.

## Compared with public classic AirPlay fingerprint

The [Unofficial AirPlay stream packet reference](https://openairplay.github.io/airplay-spec/screen_mirroring/stream_packets.html) gives the same 128-byte header, LE32 length at 0, packet type at 4, field at 6, and timestamp at 8. Honda matches the first, length, timestamp-like position and dispatch classes 0/1/2, while only explicitly reading a low type byte. This directly tests and supports the family hypothesis. Header semantics beyond the proven bytes remain opaque.

**Prior-art guard:** The pinned MHI2 `STREAM111_PROTOCOL.md` is a MU1440 target record, not used to fill any Honda field absent from the above disassembly. See `type111-transport-model.md`.
