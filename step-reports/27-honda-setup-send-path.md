# Step 27 — trace Honda SETUP response to phone-facing send

**Date:** 2026-09-29
**Starting commit:** `7c70f2f`
**Scope:** offline static analysis of local `jmcs`, current structured fixture, and research docs. No vehicle, ADB, ptrace, firmware patch, live hook, decoder, or Type-111 implementation.

## Result

The Honda SETUP output is the actual object serialized for the phone-facing HTTP response. A scan of direct call instructions in this `jmcs` ELF found one call site: `_connectionHandleMessage` (`0x28a30c`, `AirTunesServer.c`). At `0x28af72` it calls `AirPlayReceiverSessionSetup` with the receiver session in `r0`, parsed request dictionary in `r1`, and `&response` at caller stack `sp+0x54` in `r2`. If returned `OSStatus` is zero, the same `sp+0x54` value is passed in `r2` to `_requestSendPlistResponse` (`0x289f60`) at `0x28afba`.

The serializer calls `CFPropertyListCreateData` with format `0xc8` (binary plist), extracts `CFData` pointer and length, and installs them via `HTTPMessageSetBody`. The helper prepares HTTP status 200 and uses `application/x-apple-binary-plist`. `_connectionHandleMessage` later calls `HTTPConnectionSendResponse` (`0x29dbe4`) at `0x28b790`. That function commits the HTTP headers and queues response state on the connection. `_HTTPConnectionRunStateMachine` (`0x29d698`) calls `SocketWriteData` (`0x2a01c0`), which calls `writev@plt` with the connection descriptor and pending iovec data, handling partial writes. The static path reaches the TCP write syscall; runtime TCP packet segmentation and emitted packet bytes remain unobserved.

The response object is caller-owned in this observed path: `_connectionHandleMessage` releases the output object at `0x28b052`, after synchronous serialization/body installation. Setup cleans up its local response on failure; on success it publishes the response and the caller performs the release. Thus a post-Setup/pre-serializer mutation window exists in the ordinary synchronous call flow.

## Response/stream proof

The object passed to `_requestSendPlistResponse` is exactly the Setup out value, not a similarly named sibling object. Step 26 established that this object contains `streams` as a CFArray, with the stock stream dictionary carrying integer `type=110` and dynamic `dataPort`. Therefore **the stock stream response is confirmed to reach binary-plist serialization and the HTTP send path**. The fixture's Type-111 object remains synthetic; Honda acceptance is unknown.

## Request and display scope

`_connectionHandleMessage` is the request dispatcher. It obtains a parsed request body dictionary and branches into Setup. Exact server callback registration, request URI token, and any phone transaction identifier are not recovered. The response is an HTTP message with binary-plist body, status 200 on successful helper path, content type, and body length supplied from `CFDataGetLength` to `HTTPMessageSetBody`.

Display info remains separately produced by `AirPlayReceiverSessionScreen_CopyDisplaysInfo` (`0x287ae0`), which calls `ScreenCopyMain` once and returns one dictionary. No evidence places that descriptor in this SETUP response or establishes when/how it is sent to the phone. A capability augmentation point is therefore **unknown**; the known stream response augmentation candidate is the caller immediately after Setup and before serializer invocation.

## Hook and array assessment

The smallest structural candidate is the caller immediately after Setup returns (callsite `0x28af72`, before serializer callsite `0x28afba`). Stock behavior has completed; the response is available and mutable; caller ownership is visible. Appending a distinct array element preserves the existing primary entry and its position in the offline fixture. This remains only a static candidate: live-hook safety, request gating, thread/reentrancy behavior, Type-111 schema/acceptance, security association, and any capability advertisement are unknown. Display-B negotiation code is **not ready**.

## Decision summary

```text
PHONE-FACING SETUP CALLER: _connectionHandleMessage, 0x28a30c (AirTunesServer.c)
RESPONSE OUT ABI: r2=&response (caller sp+0x54); r0=session; r1=request CF dictionary; r0 return=OSStatus
RESPONSE OWNERSHIP: caller-owned +1 on success in this path; caller CFRelease after serialization
SERIALIZER: _requestSendPlistResponse, 0x289f60
WIRE FORMAT: HTTP response carrying binary plist body (format 0xc8)
SEND FUNCTION: HTTPConnectionSendResponse 0x29dbe4 -> SocketWriteData 0x2a01c0 -> writev@plt
STREAMS ARRAY REACHES PHONE: YES (static dataflow to serializer and HTTP response send)
LAST SAFE MUTATION POINT: post-Setup caller window at 0x28af72 before 0x28afba; candidate, not live-hook approval
PRIMARY ENTRY CAN REMAIN UNCHANGED: YES structurally in fixture/CFArray append model
SECOND STREAM CAN BE APPENDED: YES structurally; Honda/phone protocol acceptance UNKNOWN
DISPLAY CAPABILITY ALSO REQUIRED: UNKNOWN
STOCK-DELEGATING HOOK FEASIBLE: UNKNOWN (static caller window exists; runtime hook safety and protocol feasibility unproven)
READY FOR DISPLAY-B NEGOTIATION CODE: NO
BIGGEST BLOCKER: whether the phone negotiates an alternate display from Honda's unknown capability signaling and accepts a Type-111 entry/schema
```

## Proof graph

```text
iPhone HTTP request -> _connectionHandleMessage -> parsed request dictionary
  [HIGH CONFIDENCE: static handler/body parse; live transaction not observed]
  -> AirPlayReceiverSessionSetup
  [CONFIRMED: direct call 0x28af72]
  -> mutable response CF dictionary with streams[0] type=110 + dataPort
  [CONFIRMED: Step 26 function disassembly]
  -> _requestSendPlistResponse, same output pointer
  [CONFIRMED: direct call/dataflow 0x28afba]
  -> binary plist CFData -> HTTPMessageSetBody
  [CONFIRMED: helper disassembly]
  -> HTTPConnectionSendResponse / committed headers
  [CONFIRMED: call at 0x28b790 and function body]
  -> _HTTPConnectionRunStateMachine -> SocketWriteData -> writev(fd, iovec)
  [CONFIRMED static TCP write path; runtime packet bytes UNKNOWN]
  -> TCP/IP stack -> iPhone
  [INFERRED from connection role; no live packet capture]
```

## Verification

Ran `python3 -m unittest tests/carplay-session-model/test_display_b_fixture.py` and `git diff --check`. Fixture assertions concern synthetic model entries only. No live test was performed.
