# Honda Type-110 accepted socket read loop — Step 36

**Evidence:** exact local Honda `jmcs` ELF SHA-256 `cbc7ba881648fb8ffdfcc4c1100a028345c37134a2ae3b9dff7d76572851c232`; offline only.

## Owner and reads

```text
_ScreenThread (0x283dad)
 -> SocketAccept(listener, 10 s)
 -> accepted fd via stack +0x10
 -> NetSocket_CreateWithNative; NetSocket +4 = accepted native fd
 -> AirPlayReceiverSessionScreen_ProcessFrames (0x287d8d)
 -> NetSocket_ReadInternal (method slot +0x14, 0x2a0055)
 -> recv(fd, buffer, remaining count, flags)
```

For the protocol header, ProcessFrames calls the reader with `min=0x80`, `remaining/capacity=0x80`, and destination `screen_session+0x48`. ReadInternal loops after short positive recv results until all 128 requested bytes are filled. It returns an error on EOF before the minimum is satisfied. Then ProcessFrames reads `body_size = LE32(buffer+0)`, allocates that many bytes, and calls ReadInternal with minimum and capacity equal to body_size and destination equal to the allocation. Thus the header-complete condition is successful completion of the exact 128-byte read; the body-complete condition is successful completion of exact declared body length.

| Item | Recovered |
|---|---|
| NetSocket owner | `_ScreenThread` local wrapper; native fd at wrapper +4 |
| header buffer | screen session +0x48, 128 bytes |
| body buffer | allocation of offset-0 length |
| partial read | yes, accumulated in ReadInternal |
| EOF | short-before-minimum produces error; handler cleanup/return |
| read timeout | no specific socket-read timeout established |
| accept timeout | 10 seconds in `SocketAccept`; separate from body/header reads |
| reconnect | no reconnect loop in this thread path |
| body max check | no protocol maximum check observed before malloc in this function; ClarityLink's local parser imposes a documented configurable safety cap |

The function also calls `memset(sp+0x6c,0,0x80)` to initialize a `select()` fd_set. That is an unrelated 128-byte constant and must not be conflated with the packet header.

See `honda-screen-header.md` for field offsets and `honda-screen-framing.md` for the state machine.
