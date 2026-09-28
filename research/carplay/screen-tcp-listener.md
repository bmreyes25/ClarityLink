# Screen TCP listener trace

Scope: static review of the exact local `jmcs` ELF at commit `d347519`. No vehicle, ADB session, live capture, or firmware modification was used.

## Findings

`AirPlayReceiverSessionSetup` (`jmcs` VA `0x2854e1`) calls `ServerSocketOpen` (`0x2a0a35`); `_ScreenThread` reads a listener descriptor at thread context offset `+0x1418` and calls `SocketAccept` (`0x2a0481`) with a 10-second timeout. `SocketAccept` uses `select()` and then `accept()`. The field mapping from Setup's descriptor output at `+0x2b4` to thread context `+0x1418` is not yet reconciled interprocedurally.

The exact ELF is available locally and the full function has now been checked. In `AirPlayReceiverSessionSetup`, one UDP socket call is separate from the TCP listener call at `0x2856fe`. The TCP call supplies the address-family value from the session network-address field, `SOCK_STREAM` (`1`), `IPPROTO_TCP` (`6`), requested port `0`, a port-output pointer at session `+0x2b8`, and an FD-output pointer at `+0x2b4`. `ServerSocketOpen` supports IPv4 and IPv6 family branches and zero-initializes the address portion; the selected family is not statically fixed here. It binds port zero, calls `getsockname()`, obtains the assigned port using `SockAddrGetPort`, stores it through `+0x2b8`, and stores the descriptor through `+0x2b4`. The port is dynamic/ephemeral.

Setup passes the value from `+0x2b8` to `CFDictionarySetInt64` (`0x2945bd`). This proves insertion into the setup dictionary. The key pointer comes from a session/setup field; its semantic string is not recovered. This proves insertion into a local setup dictionary only; the dictionary’s serialization, return, or external advertisement destination has not been established.

| Item | Finding | Confidence |
|---|---|---|
| Listener creation | `ServerSocketOpen`, called by `AirPlayReceiverSessionSetup` | High |
| Listener owner/storage | outer receiver/session `+0x1418` | High |
| Transport | TCP stream socket per prior disassembly record | High |
| Bind address | Wildcard address; IPv4/IPv6 family comes from session network-address input | High |
| Bind port | Port 0 passed to bind; assigned port obtained by `getsockname()` | Confirmed |
| Port storage / dictionary | session `+0x2b8`; then `CFDictionarySetInt64` | Confirmed |
| Advertisement key | Key pointer supplied by session/setup field; semantic name unknown | Partial |
| Accepted fd storage/owner | `_ScreenThread` local `sp+0x10`, then native `NetSocket` wrapper `+4` | Confirmed |

No packet-level field is inferred here. See `accepted-fd-dataflow.md` for the first read trace.
