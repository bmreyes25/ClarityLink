# Screen thread wait and connection event

**Status: listening socket, select wait, and accept producer confirmed.**

The field at outer receiver/session offset `+0x1418` is populated by `ServerSocketOpen` (`0x2a0a34`) from `AirPlayReceiverSessionSetup`. This is a file descriptor, not a semaphore or condition object. `_ScreenThread` (`0x283dac`) loads `[r4 + 0x1400 + 0x18]` and calls `SocketAccept` (`0x2a0480`) with timeout 10 seconds. `SocketAccept` builds an `fd_set`, calls imported `select()` (`0x12d88`), and, when readable, calls imported `accept()` (`0x12f08`). The incoming connection is therefore the producer of readiness. A zero return from the wrapper causes `_ScreenThread` to call `AirPlayReceiverSessionScreen_StartSession` (`0x2883a8`, call site `0x283eb6`).

| Lifecycle action | Evidence |
|---|---|
| Initialize / create | `AirPlayReceiverSessionSetup` calls `ServerSocketOpen`; `socket`, nonblocking configuration, `bind`, and `listen` are visible in `0x2a0a34` |
| Store | returned listener fd is stored in the receiver/session field at `+0x1418` |
| Wait | `_ScreenThread` calls `SocketAccept`; helper uses `select()` and a 10-second timeout |
| Signal / post | No separate signal primitive. Remote/client TCP connection causes fd readiness; helper then accepts it |
| Accepted state | `accept()` result is returned through the helper output slot; successful return proceeds to StartSession |
| Destroy / close | cleanup paths reset the stored field and call `close()` where applicable; exact ownership on every error path is not fully audited |

**Object type:** listening socket descriptor (confirmed). **Initializer:** `ServerSocketOpen`, invoked from `AirPlayReceiverSessionSetup`. **Wait:** `SocketAccept` / `select` / `accept`. **Producer:** peer connection to the listener; request parser and accepted-socket consumer remain to be traced. No semaphore/condition-variable claim applies.
