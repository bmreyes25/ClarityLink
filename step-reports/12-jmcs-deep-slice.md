# Step 12 — recover `jmcs` socket and media slice

**Outcome: socket path substantially recovered; media backend handoff narrowed; offline static work continues.** Starting commit `62aca6a`.

## Exact binary and address map

Analyzed `extracted/system-vendor/system/bin/jmcs`, SHA-256 `cbc7ba881648fb8ffdfcc4c1100a028345c37134a2ae3b9dff7d76572851c232`. ELF32 ARM EABI5, ET_DYN; `.symtab`, DWARF, `.rel.dyn`, and `.rel.plt` are present. VA=file offset for the examined code in the first PT_LOAD. The captured process had runtime bias `0x4005a000`. No IDA/Ghidra project database was found. Full table: `research/carplay/jmcs-address-map.md`.

## Socket result

- `ServerSocketOpen` (`0x2a0a34`) calls `socket(family, type, protocol)`; the TCP caller provides family from the session sockaddr, type `1` (`SOCK_STREAM`), protocol `6` (`TCP`), and port `0`. It applies nonblocking mode through `SocketSetNonBlocking`, applies `setsockopt(fd, SOL_SOCKET=1, SO_REUSEADDR=2, &1, 4)`, and for the IPv6 branch applies `setsockopt(fd, IPPROTO_IPV6=41, IPV6_V6ONLY=26, &1, 4)`. It builds a zero-address sockaddr and calls `bind(fd, sockaddr, 16)` for IPv4 or `bind(fd, sockaddr, 28)` for IPv6. On the stream-socket path, disassembly shows `listen(fd,128)` and then `listen(fd,5)` calls. If a port output pointer is supplied, it calls `getsockname(fd, sockaddr, &socklen)` with socklen initialized to 28 and extracts the port via `SockAddrGetPort`. Failure paths close a created fd; the returned status and fd/port outputs are separate.
- The TCP call from `AirPlayReceiverSessionSetup` at `0x2856fe` uses the address family from the session network-address field, stream (`1`), TCP (`6`), requested port `0`. `ServerSocketOpen` supports IPv4/IPv6, obtains the actual port with `getsockname()`/`SockAddrGetPort`, writes it to session `+0x2b8`, and writes the fd to session `+0x2b4`.
- Setup passes the port to `CFDictionarySetInt64` (`0x2945bd`). The key string and external advertisement semantics remain unknown.
- `SocketAccept` (`0x2a0480`) takes the listener, 10-second timeout, accepted-fd out-pointer, and address pointer. It waits with `select()`, calls `accept()`, stores the fd through the out-pointer and returns status. Setup's `+0x2b4` and `_ScreenThread`'s `+0x1418` object fields are not yet reconciled.
- `_ScreenThread`'s out-pointer is stack `sp+0x10`. It wraps the accepted fd with `NetSocket_CreateWithNative`; the native descriptor is at wrapper `+4`. `NetSocket_Create` initializes read method slot `+0x14` to `NetSocket_ReadInternal`.
- `AirPlayReceiverSessionScreen_ProcessFrames` calls that method with the screen-session buffer at `+0x48` and length `0x80` (128). `NetSocket_ReadInternal` calls libc `recv()` on wrapper `+4`; it supports partial reads and retry/wait behavior. Wrapper teardown goes through `NetSocket_Delete`.
- Full TCP frame grammar remains unresolved; 128 is the first read request size, not a proven header length.

## Media result

The symbols resolve `0x8e70c` to `mc_stream_alloc_buf` and `0x8ea18` to `mc_stream_push_data`. They follow a linked media object; allocator dispatch is vtable `+0x10`, data dispatch is vtable `+0x14`. This is the stream-to-media extension boundary. `jmcs` contains named H.264/MediaCodec create, process, configure, output, Surface, stop, and destroy functions, but the linked object/table that would connect CarPlay frames to the decoder has not been resolved.

## Decision gate

## Static-analysis quality check

- The relevant socket and decoder code is present in the exact `jmcs` ELF; `jmcs` links Stagefright/media/gui and `libcarplay_proxy.so`.
- ELF symbols, DWARF and relocation tables are present. The key remaining media limitation is indirect method-table resolution, not stripped symbols.
- No IDA/Ghidra project database was located, but direct disassembly from the exact binary is available and was used for this socket/read trace.
- The accepted-fd reader is in the same `jmcs` image and is recovered; the gap is now the parser semantics and linked media object's vtable setup.
- Static analysis is not exhausted. No runtime trace is justified yet.

| Question | Result |
|---|---|
| JMCS address map | VALID |
| Listener port | Dynamic: bind port 0 then `getsockname`; exact runtime value varies |
| Port advertisement | Port is passed to `CFDictionarySetInt64`; semantic key/external advertisement unknown |
| Accepted FD owner | `NetSocket` wrapper, native fd at `+4` |
| First read | `NetSocket_ReadInternal` -> libc `recv`, 128-byte request into screen buffer `+0x48` |
| TCP parser / role | Partial / UNKNOWN |
| `0x8e70c` target | `mc_stream_alloc_buf`; linked-object vtable `+0x10` target unknown |
| H.264 / decoder / Surface | Backend functions present; stream edge / actual Surface unresolved |
| Primary binding object | NetSocket for connection; ScreenStream context/linked media-object display identity unknown |
| Static analysis exhausted | NO |
| Runtime trace needed | NO at this point; first-read gap is resolved statically |
| Ready for Display B | NO |

**Biggest blocker:** the concrete linked media-object vtable used by `mc_stream_push_data` is not traced to the H.264/MediaCodec setup and output Surface.

No tests were run because this milestone changes research documentation only; no model or executable code changed. `git diff --check` is the required validation.
