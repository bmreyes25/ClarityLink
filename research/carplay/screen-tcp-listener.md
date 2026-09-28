# Screen TCP listener trace

Scope: static review of the saved `jmcs` analysis artifacts at commit `5bdab19`. No vehicle, ADB session, live capture, or firmware modification was used.

## Findings

`AirPlayReceiverSessionSetup` (`jmcs` VA `0x2854e1`) calls `ServerSocketOpen` (`0x2a0a35`) and stores the returned descriptor at outer receiver/session offset `+0x1418`. `_ScreenThread` reads that field and calls `SocketAccept` (`0x2a0481`) with a 10-second timeout. `SocketAccept` uses `select()` and then `accept()`.

The available tracked report confirms `socket`, nonblocking configuration, `bind`, and `listen` in `ServerSocketOpen`, but the underlying detailed disassembly is ignored/untracked in this checkout. The present saved evidence does not expose the sockaddr bytes, a `getsockname()` call, or downstream use of a selected port. Therefore the exact bind address and port remain unknown; do not label the port ephemeral or assign a numeric value.

| Item | Finding | Confidence |
|---|---|---|
| Listener creation | `ServerSocketOpen`, called by `AirPlayReceiverSessionSetup` | High |
| Listener owner/storage | outer receiver/session `+0x1418` | High |
| Transport | TCP stream socket per prior disassembly record | High |
| Bind address | Unknown from tracked artifacts | Unknown |
| Bind port | Unknown from tracked artifacts | Unknown |
| Port retrieval / advertisement | No proven retrieval or advertisement edge | Unknown |
| Accepted fd storage/owner | `SocketAccept` returns into `_ScreenThread` local; further ownership transfer is not present in tracked excerpt | Partial |

The TCP listener's address/port and accepted-fd first consumer require the ignored detailed disassembly or the original analysis project. No packet-level field is inferred here.
