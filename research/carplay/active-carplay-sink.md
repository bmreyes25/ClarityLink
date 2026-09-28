# Active CarPlay sink status

The CarPlay screen path calls `mc_dev_attach("CarPlay Screen", context)` from `mc_ScreenStreamStart` at `0xBDC06`. The call reaches the generic device manager, but the matching registration and attach callback remain unknown. Therefore, the concrete sink used by this stream is still unresolved.

| Question | Finding |
|---|---|
| Requested device | `CarPlay Screen` (confirmed exact string) |
| Registration/factory | Unknown |
| Attach-created sink | Unknown |
| Active sink/ops/priv | Unknown |
| `process_data` target | Unknown for this active stream |
| H.264/MediaCodec edge | Unknown |
| Decoder cardinality and ownership | Unknown |
| Output Surface and owner | Unknown |

The generic `mc_stream_sink_ifc` layout remains DWARF-confirmed (`process_data` at +0x14). The Android MediaCodec backend exists in the ELF, but neither fact identifies this stream's concrete sink. See `mc-dev-attach.md`, `device-manager.md`, `media-vtable.md`, and `step-reports/15-carplay-device-attach.md`.
