# CarPlay control-plane state machine (offline binary trace)

**Status: socket setup and accept path confirmed; upstream dispatch remains unresolved.**

Evidence: local `jmcs` ELF and ARM/Thumb disassembly at `AirPlayReceiverSessionSetup` (`0x2854e0`), `AirPlayReceiverSessionScreen_Setup` (`0x287d5c`), `_ScreenThread` (`0x283dac`), and socket helpers (`0x2a0a34`, `0x2a0480`). This is static behavior; it does not establish a request schema or live peer behavior.

```text
AirPlayReceiverSessionSetup entry
  -> AirPlayReceiverSessionScreen_Setup (direct call site 0x28609c)
  -> create listener: ServerSocketOpen (0x2a0a34)
  -> save listener descriptor at receiver/session +0x1418
  -> optionally set socket QoS (SocketSetQoS, 0x2a08c0)
  -> _ScreenThread calls SocketAccept (0x2a0480)
  -> SocketAccept waits in select() and calls accept()
  -> accepted descriptor returned on success
  -> AirPlayReceiverSessionScreen_StartSession (0x2883a8)
  -> ScreenStream create/configure/start
```

| Transition | Function / state | Event or operation | Confidence |
|---|---|---|---|
| SESSION_SETUP -> SCREEN_CONFIGURED | `AirPlayReceiverSessionSetup` calls `AirPlayReceiverSessionScreen_Setup` at `0x28609c`; config slots at screen object `+0x10/+0x14` | Dictionary lookup/conversion | Confirmed |
| SCREEN_CONFIGURED -> LISTENER_READY | `AirPlayReceiverSessionSetup` calls `ServerSocketOpen`; stores its returned fd to outer receiver `+0x1418` | TCP listening socket creation | Confirmed |
| LISTENER_READY -> ACCEPT_PENDING | `_ScreenThread` passes fd at `r4+0x1418` to `SocketAccept` | `select()` on fd with 10-second timeout | Confirmed |
| ACCEPT_PENDING -> PEER_ACCEPTED | `SocketAccept` calls `accept()` after readiness | Incoming TCP connection | Confirmed |
| PEER_ACCEPTED -> SCREEN_STREAM_ACTIVE | `_ScreenThread` invokes `AirPlayReceiverSessionScreen_StartSession` on zero result | session start; ScreenStream lifecycle | Confirmed |
| Accepted peer -> request semantics | parser above Setup / accepted-socket consumer | Not located in the bounded xref set | Unknown |

The socket is the event mechanism: there is no evidence of a separate semaphore/condition signal at `+0x1418`. The successful `accept()` return is the wake condition. The trace does not identify the protocol carried by the accepted TCP connection.
