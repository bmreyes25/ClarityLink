# Screen TCP framing evidence

At commit `5bdab19`, the available traced path establishes listener creation and `accept()` but does not establish a `recv`, `read`, or equivalent operation on the accepted descriptor. The tracked disassembly excerpt stops before the subsequent reader implementation. Consequently no TCP header, magic, version, type, length, sequence, timestamp, flags, header size, or payload length is proven.

The length-prefixed records handled by Honda's `mc_ScreenStreamProcessData` (`jmcs` VA `0xbee91`) are a separate, proven callback-level framing layer. They must not be presented as TCP framing until a call path from accepted fd to that callback data is recovered.

| Field | Evidence-backed value |
|---|---|
| magic / version / type | Unknown |
| length / sequence / timestamp / flags | Unknown |
| header / payload length | Unknown |
| first read function, buffer, requested length | Unknown |
| SCREEN_TCP_ROLE | UNKNOWN |

For any future byte-layout recording, use neutral labels such as `field_0x00` until semantics are demonstrated. Do not fabricate packet bytes.
