# Primary CarPlay screen end-to-end trace

**Status: attachment dispatch mechanism narrowed; selected registration and media continuation unresolved.** Offline static analysis only.

## Step 25 architecture update

Prior art supports a separate secondary stream (xcertplay constants 110/111; Apple WWDC19 multiple H.264 streams). If Honda's session SETUP can be safely augmented, the Type-111 path can terminate in a ClarityLink-owned listener/decoder and bypass the runtime `mc_dev_attach("CarPlay Screen")` winner. That bypass is conditional, not yet proven on Honda. Keep the Honda primary flow unchanged; its one-main-screen display-info construction and singleton proxy registration are concrete compatibility risks. See `honda-altscreen-gap-analysis.md` and `claritylink-display-b-architecture.md`.

```text
AirPlayReceiverSessionSetup
  -> AirPlayReceiverSessionScreen_Setup                       CONFIRMED
  -> TCP listener / accepted connection / screen processing  CONFIRMED
  -> ScreenStreamProcessData -> mc_ScreenStreamProcessData   CONFIRMED
  -> mc_stream_alloc_buf / mc_stream_push_data               CONFIRMED
  -> mc_stream_sink_ifc.process_data (+0x14)                  CONFIRMED generic interface role
  -> mc_ScreenStreamStart
  -> mc_dev_attach("CarPlay Screen", stream context)          CONFIRMED
  -> devmgr_dev_attach -> devmgr_dev_alloc -> dev_attach      CONFIRMED generic dispatch
  -> callback-ranked registry lookup                            CONFIRMED generic mechanism
  -> entry matched for "CarPlay Screen"                        UNKNOWN
  -> selected entry's attach callback                           UNKNOWN
  -> concrete device and sink                                   UNKNOWN
  -> active process_data / H.264 / MediaCodec                   UNKNOWN
  -> decoder ownership/cardinality / Surface host               UNKNOWN
```

`dev_attach` scans manager entries from `+0x08`, calls each interface slot 0 and retains the strict highest score. The selected entry is passed to `dev_attach_to_app`, which invokes interface slot +4 and stores the selected entry in the device record on success. The exact comparator result for `"CarPlay Screen"` is not recovered. Generic `devmgr_app_register` and media-registration functions do not by themselves prove the selected entry.

Earlier transport evidence remains: the receiver creates an IPv4 TCP listener on port 0, obtains the assigned port via `getsockname`, and passes it to `CFDictionarySetInt64`; the semantic key/advertisement remains unknown. `_ScreenThread` accepts a connection and wraps the fd for screen processing. The first read requests 128 bytes, a receive size rather than a proven protocol header.

| Display-B media question | Verdict |
|---|---|
| Two device instances | Unknown |
| Two sinks | Unknown |
| Two decoders | Unknown |
| Two Surfaces | Unknown |
| Unique attach context per stream | Unknown |
| Display-B media path | Unknown |
| Ready for implementation | No |

See [device-registration.md](device-registration.md), [mc-dev-attach.md](mc-dev-attach.md), [carplay-decoder.md](carplay-decoder.md), and [Step 16](../../step-reports/16-carplay-registration-match.md).

## Step 17 status — winner remains unresolved (2026-09-28)

The offline pass confirms generic registration and ranking only. `dev_attach` selects the strictly highest unsigned slot `+0` result (initial best 0; ties retain the earlier node), then dispatches slot `+4`. The concrete list entry/interface/context installed for `"CarPlay Screen"` is not statically recoverable from the local `jmcs` artifact. Therefore this note does not assign an active backend, sink, decoder, or Surface. See [device-match-semantics.md](device-match-semantics.md) and [Step 17](../../step-reports/17-carplay-registration-winner.md). The exact blocker is runtime registration state (or its producer), not absent `jmcs`/DWARF. Display-B readiness remains **No**.

## Step 18 status — saved runtime captures insufficient (2026-09-28)

The offline capture audit found `/system/bin/jmcs` process/maps/status/fd snapshots and older CarPlay logs, but no registry head, candidate nodes, callback tables, contexts, or match results. `media_dev_attach` log messages are generic and are not proven to come from `mc_dev_attach("CarPlay Screen", ...)`. Registry owner is `jmcs`; known list-head field is manager `+0x08`, but its absolute runtime address and list contents are unavailable. Live observation is required to continue. See [runtime registry audit](runtime-device-registry.md) and [Step 18](../../step-reports/18-runtime-registration-resolution.md). No live action was performed.

## Step 18 live result (2026-09-29)

Read-only ADB confirmed `jmcs` PID `26577`, load base `0x4008f000`, and 45 mapped shared libraries. Current relevant logcat queries were empty. DWARF maps `mc_devs` static `0x35acbc` to candidate runtime cell `0x403e9cbc`; reading four bytes from `/proc/26577/mem` was denied (`Operation not permitted`). Manager pointer/list, winner, and slot `+4` remain unresolved. iPhone stayed disconnected. See [runtime registry evidence](runtime-device-registry.md) and [Step 18](../../step-reports/18-runtime-registration-resolution.md).
