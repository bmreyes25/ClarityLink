# Screen TCP framing evidence

The exact `jmcs` ELF establishes the first read on the accepted FD. `AirPlayReceiverSessionScreen_ProcessFrames` invokes the accepted connection's NetSocket method at `+0x14`, requesting up to `0x80` (128) bytes into the screen-session buffer at `+0x48`; the method resolves to `NetSocket_ReadInternal`, which calls `recv()` using the wrapped accepted FD. The downstream TCP record grammar remains unresolved.

The length-prefixed records handled by Honda's `mc_ScreenStreamProcessData` (`jmcs` VA `0xbee91`) are a separate callback-level framing layer; do not relabel them as the TCP transport header.

| Field | Evidence-backed value |
|---|---|
| magic / version / type | Unknown |
| length / sequence / timestamp / flags | Unknown |
| header / payload length | Unknown |
| first read function | `NetSocket_ReadInternal` (`0x2a0055`) -> libc `recv` |
| first read buffer | screen-session buffer at `+0x48` |
| requested length | `0x80` / 128 bytes; `recv` may return partial data |
| SCREEN_TCP_ROLE | UNKNOWN |

For any future byte-layout recording, use neutral labels such as `field_0x00` until semantics are demonstrated. Do not fabricate packet bytes.
