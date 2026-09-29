# Primary CarPlay screen end-to-end trace

**Status: attachment dispatch mechanism narrowed; selected registration and media continuation unresolved.** Offline static analysis only.

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
