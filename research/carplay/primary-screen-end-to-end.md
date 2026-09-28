# Primary CarPlay screen end-to-end trace

**Status: partial; device identity resolved, implementation dispatch not resolved.** Offline static analysis only.

```text
AirPlayReceiverSessionSetup
  -> AirPlayReceiverSessionScreen_Setup                     CONFIRMED
  -> TCP listener, accepted connection, screen processing    CONFIRMED
  -> ScreenStreamProcessData -> mc_ScreenStreamProcessData   CONFIRMED
  -> mc_stream_alloc_buf / mc_stream_push_data               CONFIRMED
  -> mc_stream_sink_ifc.process_data (+0x14)                  CONFIRMED interface role
  -> mc_ScreenStreamStart
  -> mc_dev_attach("CarPlay Screen", stream context)          CONFIRMED
  -> devmgr_dev_attach -> devmgr_dev_alloc -> dev_attach      CONFIRMED manager route
  -> matching device registration / attach callback           UNKNOWN
  -> concrete sink and active +0x14 target                    UNKNOWN
  -> H.264 / MediaCodec                                        UNKNOWN
  -> decoder ownership/cardinality                             UNKNOWN
  -> output Surface / Honda UI host                             UNKNOWN
```

The exact call is `mc_ScreenStreamStart` at `0xBDC06` in `jmcs`, calling `mc_dev_attach` at `0x81630`. Its first argument points to exact string `"CarPlay Screen"`; the second is loaded from `[stream_related_object + 0x78]`. The manager resolves an implementation through internal `dev_attach` (`0x81FF4`), but the matching registration/callback has not been statically identified.

Earlier transport evidence remains: `AirPlayReceiverSessionSetup` creates an IPv4 TCP listener on port 0, obtains the assigned port via `getsockname`, and passes it to `CFDictionarySetInt64`; its semantic key/advertisement remains unknown. `_ScreenThread` accepts a connection and wraps the fd for screen processing. The first read requests 128 bytes, which is a recv size and not a proven protocol header. Setup's fd field `+0x2b4` and `_ScreenThread` listener field `+0x1418` are not reconciled as the same storage.

The generic sink-interface slot and the separate MediaCodec backend are known. Neither supplies the missing edge from this registered device to a concrete sink. Two-instance feasibility and Display-B readiness remain **UNKNOWN / NO** respectively (not ready).

See `mc-dev-attach.md`, `device-manager.md`, `active-carplay-sink.md`, `carplay-decoder.md`, `decoder-surface-binding.md`, and `media-ownership-graph.md`.
