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

## Step 17 status — winner remains unresolved (2026-09-28)

The offline pass confirms generic registration and ranking only. `dev_attach` selects the strictly highest unsigned slot `+0` result (initial best 0; ties retain the earlier node), then dispatches slot `+4`. The concrete list entry/interface/context installed for `"CarPlay Screen"` is not statically recoverable from the local `jmcs` artifact. Therefore this note does not assign an active backend, sink, decoder, or Surface. See [device-match-semantics.md](device-match-semantics.md) and [Step 17](../../step-reports/17-carplay-registration-winner.md). The exact blocker is runtime registration state (or its producer), not absent `jmcs`/DWARF. Display-B readiness remains **No**.

## Step 18 status — saved runtime captures insufficient (2026-09-28)

The offline capture audit found `/system/bin/jmcs` process/maps/status/fd snapshots and older CarPlay logs, but no registry head, candidate nodes, callback tables, contexts, or match results. `media_dev_attach` log messages are generic and are not proven to come from `mc_dev_attach("CarPlay Screen", ...)`. Registry owner is `jmcs`; known list-head field is manager `+0x08`, but its absolute runtime address and list contents are unavailable. Live observation is required to continue. See [runtime registry audit](runtime-device-registry.md) and [Step 18](../../step-reports/18-runtime-registration-resolution.md). No live action was performed.

## Step 18 live result (2026-09-29)

Read-only ADB confirmed `jmcs` PID `26577`, load base `0x4008f000`, and 45 mapped shared libraries. Current relevant logcat queries were empty. DWARF maps `mc_devs` static `0x35acbc` to candidate runtime cell `0x403e9cbc`; reading four bytes from `/proc/26577/mem` was denied (`Operation not permitted`). Manager pointer/list, winner, and slot `+4` remain unresolved. iPhone stayed disconnected. See [runtime registry evidence](runtime-device-registry.md) and [Step 18](../../step-reports/18-runtime-registration-resolution.md).
