# Media vtable and active CarPlay dispatch

## Interface evidence

DWARF identifies `mc_stream_sink` as an interface prefix containing `ops` and `priv`; `mc_stream_sink_ifc.process_data` is at offset +0x14. `mc_ScreenStreamProcessData` reaches `mc_stream_alloc_buf` and `mc_stream_push_data`, which dispatch through the linked sink interface.

## Concrete table status

The exact CarPlay attachment request (`"CarPlay Screen"`) is resolved, but the manager's matching registration is not. No concrete active sink object or operations table was recovered. Consequently, entries +0x00 through +0x18 for the active sink and the target at +0x14 remain unknown. Do not substitute a generic PBS table or the MediaCodec backend table.

| Slot | Active CarPlay sink target |
|---|---|
| +0x00 | Unknown |
| +0x04 | Unknown |
| +0x08 | Unknown |
| +0x0C | Unknown |
| +0x10 | Unknown |
| +0x14 `process_data` | Unknown |
| +0x18 | Unknown |

`mc_stream_link` is a generic endpoint linker whose direct callers are PBS pipeline helpers; it does not resolve this factory. See `active-carplay-sink.md` and `mc-stream-link.md`.
