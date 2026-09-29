# Honda SETUP response: Setup to phone-facing HTTP send

**Evidence:** local `extracted/system-vendor/system/bin/jmcs`, SHA-256 `cbc7ba881648fb8ffdfcc4c1100a028345c37134a2ae3b9dff7d76572851c232`; static ARM/Thumb disassembly. No vehicle, ADB, ptrace, firmware patch, or live hook was used.

## Proven path

```text
incoming HTTP request
  -> _connectionHandleMessage (0x28a30c), AirTunesServer.c
  -> parse request body as CF property-list dictionary
  -> AirPlayReceiverSessionSetup (0x2854e0)
       r0 = receiver session
       r1 = request CF dictionary
       r2 = &response CF object (caller stack slot)
  -> response CF dictionary with streams CFArray
  -> _requestSendPlistResponse (0x289f60), same response pointer
  -> CFPropertyListCreateData(format 0xc8) -> CFData bytes and length
  -> HTTPMessageSetBody
  -> HTTPHeader_Commit
  -> HTTPConnectionSendResponse (0x29dbe4)
  -> HTTP connection's queued send state / network write
```

The critical call-site sequence is at `0x28af6a–0x28afba`: Setup receives `&sp+0x54`; on `OSStatus == 0`, that same slot is loaded into `r2` for `_requestSendPlistResponse`. After the helper returns, `_connectionHandleMessage` releases the response at `0x28b04e–0x28b054`. The helper serializes synchronously before returning. Setup stores its dictionary through its caller-provided pointer at `0x286260` and invokes its completion callback separately.

## Request/response facts

`_connectionHandleMessage` is the phone-facing HTTP request dispatcher for this path. It consumes an HTTP message, obtains/parses a property-list request dictionary, calls Setup, then prepares the HTTP response. The server's registration edge into `_connectionHandleMessage` is outside this call slice; the exact route token/path is not asserted here. Setup failure skips plist serialization and follows the status response path.

`_requestSendPlistResponse` initializes HTTP status 200, calls `CFPropertyListCreateData` with format value `0xc8` (the binary plist format used by this implementation), reads `CFData` bytes and length, and passes both to `HTTPMessageSetBody`. The binary-plist content type constant resolves to `application/x-apple-binary-plist`. `HTTPConnectionSendResponse` commits the HTTP header and records the response/message body in the connection's outgoing state. `_HTTPConnectionRunStateMachine` (`0x29d698`) calls `SocketWriteData` (`0x2a01c0`), which calls `writev@plt` on the connection descriptor and handles partial writes by advancing the iovec. The static path therefore reaches the TCP write syscall; runtime packet segmentation is not observed.

## Confidence

| Claim | Result |
|---|---|
| Setup has a phone-request caller | **CONFIRMED**: direct call from `_connectionHandleMessage` |
| `streams` response reaches serializer | **CONFIRMED**: same output pointer passed as serializer input |
| Serializer and wire representation | **CONFIRMED**: binary property list in HTTP response body |
| Response ownership | **CONFIRMED caller-owned +1 in observed path**: caller releases after serializer returns |
| Exact HTTP server callback registration edge | **UNKNOWN** in this bounded trace |
| TCP write syscall | **CONFIRMED**: HTTP state machine -> `SocketWriteData` -> `writev@plt` |
| Runtime packet segmentation/bytes | **UNKNOWN**: no live transaction capture |
| iPhone acceptance of an appended Type-111 entry | **UNKNOWN** |

The response is mutable after Setup returns and until the synchronous plist serialization call begins. The call site leaves a narrow post-Setup/pre-serializer interval, but thread/reentrancy implications and Type-111 protocol correctness are still unknown. This identifies a candidate mutation location, not authorization to implement a live hook.
