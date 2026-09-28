# Primary CarPlay screen end-to-end trace

**Status: PARTIAL.** Static/offline analysis of the exact local `jmcs` ELF; no vehicle, ADB, firmware, or live capture work.

```text
AirPlayReceiverSessionSetup
  -> AirPlayReceiverSessionScreen_Setup                      CONFIRMED
  -> ServerSocketOpen(AF_INET, SOCK_STREAM, TCP, port=0)      CONFIRMED
  -> getsockname() -> assigned port -> +0x2b8                 CONFIRMED
  -> CFDictionarySetInt64(port)                                CONFIRMED
  -> semantic dictionary key / external advertisement        UNKNOWN

TCP listener (+0x1418 in _ScreenThread context)
  -> select() -> accept()                                     CONFIRMED
  -> accepted fd at _ScreenThread stack +0x10                 CONFIRMED
  -> NetSocket_CreateWithNative; wrapper +4 stores native fd  CONFIRMED
  -> AirPlayReceiverSessionScreen_ProcessFrames               CONFIRMED
  -> vtable +0x14 -> NetSocket_ReadInternal -> recv(...128)   CONFIRMED
  -> ScreenStreamProcessData -> mc_ScreenStreamProcessData    CONFIRMED
  -> mc_stream_alloc_buf / mc_stream_push_data                CONFIRMED
  -> linked media object vtable +0x14 concrete target         UNKNOWN
  -> H.264 decoder and actual output Surface                   UNKNOWN
```

The `jmcs` address map and exact-file hash are in `jmcs-address-map.md`. The TCP `ServerSocketOpen` call in `AirPlayReceiverSessionSetup` requests port 0 and supplies output fields at session `+0x2b8` (assigned port) and `+0x2b4` (fd). The function binds a zero-initialized wildcard sockaddr using the session's address family, obtains the selected port using `getsockname()` and `SockAddrGetPort`, and passes that value to `CFDictionarySetInt64`. The dictionary key's semantic name and how this field is externally advertised are not established.

The offset relationship between Setup's output fd field `+0x2b4` and `_ScreenThread`'s listener field `+0x1418` is not reconciled yet. The accept/read lifecycle itself is proven, but these fields are not asserted as identical locations.

The successful accepted fd is stored via `_ScreenThread`'s output pointer at `sp+0x10`, wrapped by `NetSocket_CreateWithNative`, and read through `NetSocket_ReadInternal`. The first request is 128 bytes into a screen-session buffer; this is a `recv()` request size, not proof of a 128-byte protocol header. Full TCP record semantics remain unknown.

Honda's `mc_ScreenStreamProcessData` calls `mc_stream_alloc_buf` (`0x8e70c`, vtable slot `+0x10`) and `mc_stream_push_data` (`0x8ea18`, vtable slot `+0x14`). The linked object's actual table is not identified. `jmcs` also contains a real MediaCodec/H.264 backend (`android_mediacodec_create`, `android_mediacodec_process_data`, `initialize_codec`, surface functions), but no evidence-backed edge yet joins this callback's linked object to that backend.

## Structural decision

| Component | Two instances supported by evidence? |
|---|---|
| Screen session objects | UNKNOWN |
| TCP listeners | UNKNOWN |
| ScreenStreams | UNKNOWN end-to-end; generic APIs are instance-shaped |
| Decoders | UNKNOWN |
| Output Surfaces | UNKNOWN |
| Callback can route streams | PARTIAL: stream/context and linked-object interfaces exist; display identity/targets unknown |

Generic screen registry and stream counters exist, but Honda initialization registers one `gMainScreen`, display info comes from `ScreenCopyMain`, and proxy callback registration is singleton. Latent multi-screen support remains **PARTIAL**; R15 support is not evidenced.

**Raw TCP capture: NOT REQUIRED to resolve the first read**, which static analysis recovered. A capture remains **HELPFUL** only if subsequent offline analysis cannot resolve the accepted TCP record semantics or external port advertisement. The local bind port is dynamic, so any future capture would first need to observe the runtime endpoint. No USB analyzer is indicated.

**Ready for Display B implementation: NO.** Static analysis is **not exhausted**: the exact binary, symbols, DWARF, and relocations are available. The main remaining static blocker is linking the CarPlay media object to the MediaCodec backend through its vtable construction.


## Media/backend evidence update (Step 13)

`mc_stream_push_data` -> `mc_stream_sink_ifc.process_data` (+0x14) is confirmed by DWARF layout and callsite. The active sink target remains unresolved. A separate Android MediaCodec backend is present; its per-context structure contains codec, dimensions, surface context, and buffer vectors, and its surface setter configures through a `SurfaceTextureClient`. The CarPlay call edge into that backend and H.264 remains unknown. See `media-object.md`, `media-vtable.md`, and `decoder-surface-binding.md`.
