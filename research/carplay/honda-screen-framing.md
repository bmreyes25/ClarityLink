# Honda screen-stream framing — Step 34

This note separates the TCP receive boundary from the downstream screen-record parser.

## Accepted connection

Honda creates the Type-110 listener during `AirPlayReceiverSessionSetup`. `_ScreenThread` waits in `SocketAccept` on a listener fd held in its thread context; on success, the accepted fd is wrapped by `NetSocket_CreateWithNative`. That `NetSocket` wrapper owns the accepted native fd while `_ScreenThread` calls `AirPlayReceiverSessionScreen_ProcessFrames`. The initial read requests up to 128 bytes into screen-session buffer `+0x48` through `NetSocket_ReadInternal`/`recv`; partial reads are handled. The wrapper is released on thread cleanup.

The connection is associated with the listener it arrived on. That gives a transport-level binding to that setup/listener generation without needing a display UUID at the socket layer. Honda's static artifacts do not yet reconcile Setup's listener output at session `+0x2b4` with `_ScreenThread`'s context `+0x1418`, so exact long-lived object ownership remains partial.

## Framing boundary

The TCP byte grammar is not yet recovered. A 128-byte *read request* is not evidence of a 128-byte packet header. Likewise, `mc_ScreenStreamProcessData`'s callback-level length-prefixed records are downstream and must not be mislabeled as the TCP envelope.

| Item | Honda evidence |
|---|---|
| listener | ephemeral TCP listener from Type-110 setup |
| accepted-fd owner | native fd stored in per-thread `NetSocket` wrapper |
| first receive | `recv`, requested maximum 128 bytes; may be partial |
| TCP header fields / size | Unknown |
| timestamp / payload length / encryption boundary | Unknown at TCP framing layer |
| screen-record parser | downstream `ProcessFrames` then stream-data processing; full record format not recovered in this repository |
| VideoConfig / H.264 extraction | not fully recovered for this exact Honda binary |

MHI2's documented 128-byte ScreenStream header and VideoConfig handling belongs to its exact MU1440 target, and must not be copied as Honda fact. The first useful Type-111 framing milestone is recovering Honda's parser after `ProcessFrames` with exact record offsets and crypto boundary, without saving key material.
