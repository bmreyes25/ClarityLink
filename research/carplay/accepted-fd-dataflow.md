# Accepted descriptor dataflow

Scope: exact local `jmcs` ELF at commit `62aca6a`; SHA-256 and address mapping are recorded in `jmcs-address-map.md`.

## Listener and accept

`AirPlayReceiverSessionSetup` calls `ServerSocketOpen` at `0x2856fe` for a TCP stream socket (`SOCK_STREAM=1`, `IPPROTO_TCP=6`, requested port `0`). Address family comes from the session network-address field; `ServerSocketOpen` handles IPv4 and IPv6. The call supplies output pointers for port at session `+0x2b8` and descriptor at `+0x2b4`. It binds a zero-initialized address at port zero, calls `getsockname()` when the port-output pointer is non-null, extracts the port through `SockAddrGetPort`, stores it through `+0x2b8`, and stores the descriptor through `+0x2b4`. Setup then passes the port value to `CFDictionarySetInt64` (`0x2945bd`); the dictionary key is a session/setup field whose semantic name is not recovered.

`_ScreenThread` calls `SocketAccept` (`0x2a0480`) at `0x283de4` with listener fd `[thread context +0x1418]`, 10-second timeout, and accepted-fd output pointer `sp+0x10`. `SocketAccept` calls `select()` on the listener, then `accept()`. On success it stores the returned fd through that output pointer and returns status 0, not the fd.

## Handoff to first read

`_ScreenThread` loads the accepted fd from `sp+0x10` and calls `NetSocket_CreateWithNative` (`0x2a0679`) with output pointer `sp+0x0c` and the fd. That wrapper calls `NetSocket_Create` and stores the native fd in the resulting object at `+4`; `_ScreenThread` retains the wrapper at `sp+0x0c`.

The thread passes that wrapper to `AirPlayReceiverSessionScreen_ProcessFrames` (`0x287d8d`). The function invokes the wrapper's read method at slot `+0x14`, using the screen-session buffer at `+0x48` and requested length `0x80` (128 bytes). `NetSocket_Create` initializes slot `+0x14` to `NetSocket_ReadInternal` (`0x2a0055`). On the native-socket path, `NetSocket_ReadInternal` obtains fd from wrapper `+4` and calls libc `recv(fd, buffer, remaining_length, flags)`. The first request has 128 bytes remaining; the read loop handles partial reads and retry/wait cases.

```text
ServerSocketOpen -> output fd session +0x2b4; output port +0x2b8
                 -> getsockname -> CFDictionarySetInt64(port)
_ScreenThread -> SocketAccept(listener, ..., &stack[0x10])
              -> accepted fd at stack[0x10]
              -> NetSocket_CreateWithNative(&stack[0x0c], accepted fd)
              -> NetSocket wrapper +4 = native fd
              -> ProcessFrames -> wrapper slot +0x14
              -> NetSocket_ReadInternal -> recv(fd, screen buffer, 128, flags)
```

The `_ScreenThread` cleanup path passes the wrapper to `NetSocket_Delete` (`0x29fcdc`), the wrapper lifecycle/close path. The accepted fd is owned by the native NetSocket wrapper during frame processing; no ScreenStream field has been proven to hold it. The object-offset relationship between Setup's output field `+0x2b4` and `_ScreenThread`'s listener field `+0x1418` has not yet been reconciled, so those locations are recorded separately.

## Remaining boundary

This proves the first read, buffer and requested length, but not the complete TCP grammar or semantic port key. See `screen-tcp-framing.md`. No live session is needed to establish the first `recv()` edge.
