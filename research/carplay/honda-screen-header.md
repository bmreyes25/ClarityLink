# Honda Type-110 screen header — Step 36

**Binary:** identity-verified `jmcs`, SHA-256 `cbc7ba881648fb8ffdfcc4c1100a028345c37134a2ae3b9dff7d76572851c232`; offline static analysis.

## Conclusion

**Honda header size: 128 bytes (confirmed).** The size alone was not used as proof. In `AirPlayReceiverSessionScreen_ProcessFrames` (`0x287d8d`), `NetSocket_ReadInternal` is called with both required/minimum bytes and read capacity set to `0x80`; it returns only after accumulating that count (short positive `recv` results loop). The resulting 128-byte buffer begins at screen-session `+0x48`. Honda then reads a 32-bit word at buffer `+0` as the next body read length, reads one byte at `+4` for its message switch, and reads bytes at `+8` as a 64-bit timestamp input. Thus the fixed read is followed by a separate body read of the header-declared size.

The same function has a `memset(..., 0, 0x80)` call, but that call initializes the local `fd_set` passed to `select`; it is unrelated to the protocol header. This independent constant use was specifically distinguished from the exact 128-byte socket read.

## Honda fields recovered

| Offset | Size | Endian / representation | Honda use | Semantic status |
|---:|---:|---|---|---|
| `0x00` | 4 | little-endian unsigned integer (ARM little-endian `ldr`) | Used directly as the body allocation and exact second-read length | Body byte count, excludes fixed header because it is read after the header |
| `0x04` | 1 byte read | byte | Switch values compared: `0`, `1`, `2`, `5`, `4`; other values take unrecognized/log path | Message discriminator; byte 5 of the apparent classic 16-bit field is not checked by this branch |
| `0x05` | 1 | — | No proven read in this path | Unknown |
| `0x06` | 1 byte bit access | bit 1 copied to a screen-session flag in the config branch | In type-1 branch, bit 1 is copied into a session flag used by later timestamp-conversion selection; broader protocol meaning unknown |
| `0x07` | 1 | — | No proven read | Unknown |
| `0x08` | 8 | little-endian 64-bit load | Passed to a session timestamp-conversion callback when installed | Timestamp-like value; exact wire time format is not proven by Honda code alone |
| `0x10` | 4 | IEEE-754 binary32, little-endian target | Config branch loads and converts it to a CF double property | Value/property meaning unknown |
| `0x14` | 4 | IEEE-754 binary32, little-endian target | Config branch loads and converts it to a second CF double property | Value/property meaning unknown |
| `0x18..0x7f` | 104 | — | No semantic interpretation established in the bounded pass | Unknown; raw header preserved by ClarityLink parser |

## Length and encryption ordering

The first field is loaded before the body read, passed to `malloc`, and passed as both requested minimum and receive length to `NetSocket_ReadInternal`. No protocol maximum is visible in this function before allocation. When the screen security flag at session `+0x1e4` is set, `AES_CTR_Update` is then called on the separate body allocation; the header remains plaintext. Message dispatch follows decryption.

## External family comparison

The [Unofficial AirPlay screen packet reference](https://openairplay.github.io/airplay-spec/screen_mirroring/stream_packets.html) describes a 128-byte header, LE32 payload length at offset 0, a 16-bit packet type at offset 4, a 16-bit field at offset 6, and an 8-byte NTP timestamp at offset 8. Honda independently confirms the 128-byte length/body split, LE32 body size, low type byte dispatch, a bit use in byte 6, and an 8-byte timestamp-like value at offset 8. The discrepancy is that Honda's observed dispatch loads one byte at offset 4 and does not validate the type's high byte. This is a strong family match with a Honda-specific/partial field interpretation, not proof all 128 bytes or classic semantics are identical.

**Result:** `HONDA_HEADER_SIZE=128`; `OFFSET_0_BODY_LENGTH=CONFIRMED, LE32`; `MESSAGE_TYPE=byte at +4`; `TIMESTAMP_LIKE=8 bytes at +8, exact format unknown`.
