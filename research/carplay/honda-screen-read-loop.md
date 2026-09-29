# Honda Type-110 accepted socket read loop — Step 35

**Evidence scope:** exact offline Honda `jmcs` ELF SHA-256 `cbc7ba881648fb8ffdfcc4c1100a028345c37134a2ae3b9dff7d76572851c232`; no live session, key bytes, ADB, or ptrace.

## Ownership and first read

```text
_ScreenThread (0x283dad)
  -> SocketAccept(listener from thread context +0x1418, timeout 10 s)
  -> accepted native fd returned through stack +0x10
  -> NetSocket_CreateWithNative(&stack+0x0c, fd)
       NetSocket object +4 = native fd
       method slot +0x14 = NetSocket_ReadInternal (0x2a0055)
  -> AirPlayReceiverSessionScreen_ProcessFrames (0x287d8d)
  -> NetSocket_ReadInternal -> recv(fd, screen-session buffer +0x48, 0x80, flags)
```

| Requested item | Recovered value |
|---|---|
| Owner object | Per-thread `NetSocket` wrapper during processing; native fd at wrapper +4 |
| Read function | `NetSocket_ReadInternal` (`0x2a0055`) through vtable/method slot +0x14 |
| Buffer | Screen-session object buffer at +0x48 |
| Initial request size | 128 bytes (`0x80` maximum), not a demonstrated header length |
| State object | ProcessFrames local receive state plus screen-session buffer; persistent connection ID fields are not fully reconciled |

## Loop behavior supported by the artifacts

The read loop requests the remaining portion of a requested buffer and treats short positive reads as partial progress, invoking the read method again for the remaining count. The native path reaches `recv()` on the wrapped accepted fd. The thread uses a 10-second listener-accept timeout before it owns a peer socket. On thread cleanup it deletes/releases the NetSocket wrapper.


| Behavior | Evidence / limit |
|---|---|
| Partial read | ReadInternal tracks remaining requested bytes and retries until satisfied or an error/status occurs. The exact retry/error mapping is not fully recorded in the saved excerpts. |
| EOF | Not characterized beyond the read method returning a nonzero status into ProcessFrames cleanup/error handling. |
| Timeout | 10 seconds is proven for `SocketAccept`'s `select`; do not apply this as a proven socket-read timeout. |
| Reconnect | No reconnect loop is established; `_ScreenThread` accepts one fd for its processing generation and cleanup releases its wrapper. |
| Fixed packet size | Unknown. A 128-byte `recv` request is only a maximum read request. |

**Evidence:** `research/carplay/accepted-fd-dataflow.md`, `research/carplay/screen-tcp-framing.md`, ELF disassembly function `AirPlayReceiverSessionScreen_ProcessFrames` at VA `0x287d8d`, `_ScreenThread` at `0x283dad`, and `NetSocket_ReadInternal` at `0x2a0055`.
