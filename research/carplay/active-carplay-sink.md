# Active CarPlay sink status

The active screen path requests `mc_dev_attach("CarPlay Screen", context)` from `mc_ScreenStreamStart` at `0xBDC06`. Generic dispatch is now partially recovered: the device manager ranks registered interfaces by each slot-0 callback, then calls slot +4 on the winning entry through `dev_attach_to_app`.

| Question | Finding |
|---|---|
| Requested device | `CarPlay Screen` (confirmed exact string) |
| Registry API | `devmgr_app_register` (confirmed generic API) |
| Matching registration/comparator | Unknown for this key |
| Attach callback | Unknown for this key |
| Attach-created sink | Unknown |
| Active sink/ops/priv | Unknown |
| `process_data` target | Unknown for this active stream |
| H.264/MediaCodec edge | Unknown for this active stream |
| Decoder cardinality | Unknown |
| Output Surface and owner | Unknown |

The generic `mc_stream_sink_ifc.process_data` slot at +0x14 remains DWARF-confirmed. The Android MediaCodec backend exists in the ELF, but neither generic interface evidence nor backend presence identifies the concrete sink selected for this stream. See [device-registration.md](device-registration.md), [carplay-decoder.md](carplay-decoder.md), and [Step 16](../../step-reports/16-carplay-registration-match.md).
