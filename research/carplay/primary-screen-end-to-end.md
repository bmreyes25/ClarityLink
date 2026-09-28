# Primary CarPlay screen end-to-end trace

**Status: PARTIAL.** Static/offline scope at commit `5bdab19`; no vehicle, ADB, firmware, or live capture work.

```text
CarPlay session setup
  -> AirPlayReceiverSessionScreen_Setup                 CONFIRMED
  -> ServerSocketOpen; listener fd stored at +0x1418    CONFIRMED
  -> port/address retrieval and advertisement            UNKNOWN
  -> iPhone connects / accepted fd                       HIGH CONFIDENCE
  -> accepted-fd owner and first read                    UNKNOWN
  -> TCP framing/parser                                  UNKNOWN
  -> AirPlayReceiverSessionScreen_StartSession          CONFIRMED after accept
  -> generic ScreenStream create/configure/start         CONFIRMED
  -> ScreenStreamProcessData global callback             CONFIRMED
  -> Honda mc_ScreenStreamProcessData                    CONFIRMED
  -> callback record framing / 0x8e70c dispatch          CONFIRMED
  -> concrete target assigned to [object+0x10]           UNKNOWN
  -> H.264 boundary                                      UNKNOWN
  -> decoder creation/ownership                          UNKNOWN
  -> output Surface creation/binding                     UNKNOWN
```

`AirPlayReceiverSessionSetup` (`0x2854e1`) calls `ServerSocketOpen` (`0x2a0a35`) and stores its returned descriptor at outer receiver/session offset `+0x1418`. `_ScreenThread` (`0x283dad`) passes that descriptor to `SocketAccept` (`0x2a0481`), which uses `select()` then `accept()`. A successful return calls `AirPlayReceiverSessionScreen_StartSession` (`0x2883a9`). StartSession creates/configures/starts a generic `ScreenStream`.

`ScreenStreamProcessData` (`0x28e2c9`) dispatches through a process-global callback. Honda `mc_ScreenStreamProcessData` (`0xbee91`) parses callback-level records and calls `0x8e70c`, which dispatches through an object slot at `+0x10`; the assigned target is not recovered. The callback-level record framing is not evidence of the accepted TCP framing.

The same ELF has H.264/AVCC helpers and Android MediaCodec imports, including `configure` with a `SurfaceTextureClient` parameter, but no proven call/object edge joins them to this callback. The display-specific Surface remains unknown.

## Structural decision

| Component | Two instances supported by evidence? |
|---|---|
| Screen session objects | UNKNOWN |
| TCP listeners | UNKNOWN |
| ScreenStreams | UNKNOWN end-to-end; generic APIs are instance-shaped |
| Decoders | UNKNOWN |
| Output Surfaces | UNKNOWN |
| Callback can route streams | PARTIAL: stream argument/context API exist; display identity/target mapping unknown |

The narrow saved-artifact search found generic screen registry and stream counters, but Honda initialization registers one `gMainScreen`; display info comes from `ScreenCopyMain`, and the Honda proxy callback registration is singleton. Existing audit finds no positive R15/view-area/safe-area implementation evidence. **Latent multi-screen support: PARTIAL** (generic primitives exist; car-specific negotiated support is not evidenced).

**Raw TCP capture: HELPFUL** after resolving the listener endpoint locally. One short peer-to-head-unit TCP startup window could identify the accepted flow's application framing and role. It would not resolve the decoder/Surface edge unless payload delivery is correlated with the callback. No USB analyzer is presently indicated.

**Ready for Display B implementation: NO.** Primary path is incomplete. Biggest blocker: the saved analysis lacks a proven accepted-fd reader-to-callback edge, including listener endpoint and TCP parser.
