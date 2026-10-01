# Step 43H — HTTP commit failure and project-child cleanup lifecycle

**Date:** 2026-10-01
**Starting HEAD:** `d3fd5d367d4c097b3b20b0a9aa11cd4ad955448e`
**Scope:** offline static ARM/Thumb audit and synthetic lifecycle model only.

## 1. Preserved Step 43G state and artifact

At start, Step 43G changes were present locally and uncommitted: VA mapper/tests, callback evidence, Type110 ledger, synthetic delivery model/tests, and Step 43G report/research notes. They were preserved. The verified artifact is `extracted/system/system/bin/jmcs`, SHA-256 `cbc7ba881648fb8ffdfcc4c1100a028345c37134a2ae3b9dff7d76572851c232` (reference match YES). Step 43G callback and ownership findings remain intact.

## 2. Tools and method

Used Apple `llvm-objdump` from Xcode, the checked-in preserved symbols/disassembly reports, `shasum`, the Step 43G VA mapper and standard-library tests, plus the repository test runner in its documented local `.venv`. No Honda code was executed. No vehicle, ADB, firmware or binary mutation, hook, keys, capture, Type111 implementation, or live test was used.

## 3. HTTP response path

```text
_connectionHandleMessage 0x28a30c
  ├─ _requestSendPlistResponse 0x289f60
  │    ├─ HTTPHeader_InitResponse 0x29dccc
  │    ├─ CFPropertyListCreateData 0x28e6fc (synchronous)
  │    └─ HTTPMessageSetBody 0x29d01c
  ├─ status/header fields: HTTPHeader_SetField 0x29de80
  └─ HTTPConnectionSendResponse 0x29dbe4 at caller 0x28b790
       ├─ HTTPHeader_Commit 0x29dd18
       ├─ prepare connection-context iovecs
       └─ set connection state [connection+0xc0] = 1
            ↓
_HTTPConnectionRunStateMachine 0x29d698 → SocketWriteData 0x2a01c0 → writev
```

The response bytes/header reside in HTTP message/context buffers. `HTTPConnectionSendResponse` has no `writev` call. After its `LogHTTP` call, the send-preparation path writes connection-context iovec fields and changes the connection state; no separate enqueue/allocation helper is called. No separate queue/list insertion was recovered at this site: the current state-machine callback returns and the loop sees state 1.

## 4. Commit failure propagation

`HTTPHeader_Commit` returns nonzero for its audited invalid cases: it returns the stored nonzero committed marker if already committed; `-6745` for an empty header; and `-6751` if appending CRLF would reach/exceed the 0x2000-byte header bound. These values are literal signed 32-bit status returns from the reference ELF. On nonzero return, `HTTPConnectionSendResponse` returns immediately before populating the write iovecs or setting state 1.

At `0x28b790`, `_connectionHandleMessage` calls `HTTPConnectionSendResponse` and branches directly to the common epilogue path. It does not overwrite the call's `r0` result. The handler returns that status to `_HTTPConnectionRunStateMachine`, which calls the handler through `[connection+0x28]` at `0x29d6ea`, checks `r0` at `0x29d6f2`, and routes nonzero to `HTTPConnectionStop` plus callback `[connection+0x20]` at `0x29d752–0x29d75e`. Accepted server connections install `_HTTPServerCloseConnection` at that callback slot. Thus commit failure is not ignored or retried: it closes the connection through the terminal callback path.

| Failure site | Return | Caller behavior | Connection effect | Session effect | Confidence |
|---|---|---|---|---|---|
| Plist creation failure | `_requestSendPlistResponse` produces 500 | Handler prepares error status response | Still attempts status response | No direct teardown | HONDA_CONFIRMED |
| Body install failure | helper produces 500 and stores body error | Handler prepares error status response | Still attempts status response | No direct teardown | HONDA_CONFIRMED |
| InitResponse/SetField error | nonzero helper status | handler returns nonzero | state machine stops and closes | finalizer teardown if context has session | HONDA_CONFIRMED |
| Commit empty/oversized/already-committed error | `-6745`, `-6751`, or stored marker | `HTTPConnectionSendResponse` returns it; handler propagates | state machine stops and closes | finalizer teardown if context has session | HONDA_CONFIRMED |
| State 1 socket terminal error | nonzero socket status | state machine failure branch | stops and closes | finalizer teardown if context has session | HONDA_CONFIRMED |

## 5. Bounded HTTP state machine

| State | Operation | Success | Retry/partial | Terminal error |
|---|---|---|---|---|
| 0 | Read HTTP message; invoke handler | handler returns zero and loop re-reads connection state | status 11 yields through read dispatch source | read error or nonzero handler result stops and calls failure callback |
| 1 | Write prepared response iovec | fully written; reset messages and restore state 0 when keep-alive flag requests it | `EINTR` retried in `SocketWriteData`; `EAGAIN` or positive partial write becomes status 11; iovec is updated and write dispatch resumes/yields | other socket status stops connection and invokes failure callback |

`UpdateIOVec` (`0x29fc94`) consumes full iovec entries, advances the active base/length for a partial entry, updates remaining count, and returns 11 while bytes remain; it returns zero when complete. `SocketWriteData` (`0x2a01c0`) explicitly retries errno 4 (`EINTR`); other errno values propagate, except the state machine specially recognizes 11 as retry. This is a bounded audit of response sending, not all HTTP state behavior.

## 6. Lifecycle chain classification

| Edge | Finding | Classification |
|---|---|---|
| Serialized response → HTTP body | synchronous plist CFData, then body attachment | CONFIRMED |
| Handler → HTTPConnectionSendResponse | direct call at `0x28b790` | CONFIRMED |
| HTTPConnectionSendResponse → state 1 | commit succeeds, iovecs prepared, state field set | CONFIRMED |
| Commit failure → handler return | exact `r0` preserved through common epilogue | CONFIRMED |
| Handler nonzero → state machine close path | indirect callback result checked; stop/callback branch | CONFIRMED |
| Close callback → HTTP connection release | `_HTTPServerCloseConnection` unlinks, stops, releases | CONFIRMED |
| Connection finalizer → session teardown | conditional on private context `+0xf4` non-null | CONFIRMED, conditional |
| Every HTTP connection has exactly one parent session | not proven | UNKNOWN |
| Project child subscribes to parent teardown | no supported subscription point found | UNKNOWN |

## 7. Connection/session ownership and teardown

`_connectionFinalize` (`0x289d90`) obtains private context via `[connection+8]`; if session at context `+0xf4` is non-null, it calls `AirPlayReceiverSessionTearDown(session, NULL, reason, NULL)` at `0x289dc6`, then releases and clears that session pointer. This is a conditional connection-to-session edge. Multiplicity/reuse of a session across connections is not established.

For null params, `AirPlayReceiverSessionTearDown` (`0x2852ec`) makes a platform-control call first, then executes the full cleanup sequence: session-end bookkeeping; `_ScreenTearDown`; `_TearDownStream` twice for stream slots; `_ControlTearDown`; `_TimingFinalize`; `AirTunesClock_Finalize`; dispatch source cancel/release/clear. `_ScreenTearDown` (`0x284628`) sends stop command `0x71`, joins the screen worker if active, closes a nonnegative screen-session descriptor, sets it to `-1`, and clears its started flag. `_TearDownStream` (`0x284bd8`) stops/joins a stream worker, closes nonnegative stream descriptors and sets them to `-1`, frees RTP jitter/ring buffers, and clears state. The caller finalizer releases the session after teardown returns. No session-wide repeated-teardown guard, accepted ScreenStream socket ownership, or crypto-zeroization behavior was established by this bounded trace.

HTTP control connection and Type110 Screen listener have separate fields and teardown code. The audit does not equate HTTP connection lifetime with an accepted ScreenStream TCP socket lifetime.

## 8. Attachment candidates and cleanup contract

Candidates assessed: wrapping `AirPlayReceiverSessionTearDown`; observing its existing `AirPlayReceiverSessionPlatformControl` call; `_connectionFinalize`; `_ScreenTearDown`; and a generic delegate callback. The first would cover only callers integrated through this internal function; connection finalization covers only connection destruction and non-null session context; screen teardown is Type110-specific. PlatformControl is called at teardown entry, but its arguments/API do not establish a project-child notification contract. No dedicated project callback/API was recovered.

```text
PROJECT_CHILD_ATTACHMENT_POINT: UNKNOWN
```

The synthetic contract latches `STOPPING`/`STOPPED`, closes project listener and accepted socket once, releases parser/decoder state once, and never releases or mutates Honda Type110/audio/center-screen objects. Project-only setup, response-insertion, serialization, commit, and scheduling errors clean only project state. Partial/EAGAIN writes remain pending. Terminal delivery failure is not equated with parent teardown until the Honda session teardown event is observed. Honda parent teardown dominates the child; resulting stock changes are attributed to Honda, not project cleanup. The detailed contract is in `research/carplay/honda-project-child-lifecycle-contract.md`.

## 9. Synthetic failure matrix

Extended the synthetic-only model/tests for allocation failure, listener failure, response insertion failure, serialization failure, HTTP commit failure, state-machine scheduling failure, partial write, retryable result, terminal write/peer event, connection finalize, parent session teardown, repeated teardown, already-stopped child, exactly-once listener/socket/decoder cleanup, Type110 response/crypto preservation, screen and audio preservation on project-only failure, and parent-only stock transition. These are `SYNTHETIC_TEST_VALUE`; they do not prove Honda callback APIs.

## 10. Tests

Created documented `.venv` and installed only `requirements-test.txt` (`pytest>=8.3,<9`); no global Python was changed. `PYTHON="$PWD/.venv/bin/python" ./tools/run_tests.sh`: 241 passed, 4 skipped; locator smoke 3 passed; all three simulator JS checks and Type111 failure twin passed; runner's diff check passed. Step 43G VA mapper's 8 tests are included in the pytest suite. No test ran Honda code.

## 11. Remaining unknowns and readiness

Unknown: a supported project child attachment point spanning every parent teardown source; whether sessions are shared/reused across HTTP connections; accepted ScreenStream socket linkage; exact teardown behavior for every partial teardown; crypto clearing. No Type111 implementation or live readiness follows.

```text
SETUP RESPONSE CALLBACKS: PROVEN (Step 43G)
STREAMS ARRAY CALLBACKS: PROVEN (Step 43G)
TYPE110 CONTAINER OWNERSHIP: PROVEN (Step 43G)
SERIALIZATION BOUNDARY: PROVEN (Step 43G)
HTTP RESPONSE COMMIT PATH: PROVEN
HTTP COMMIT FAILURE EFFECT: CONNECTION_CLOSE
HTTP STATE MACHINE: PROVEN (bounded response states)
TERMINAL SOCKET FAILURE: PROVEN
CONNECTION FINALIZE → SESSION TEARDOWN: PROVEN (conditional on non-null context session)
SESSION TEARDOWN ORDER: PARTIAL
PROJECT CHILD ATTACHMENT POINT: UNKNOWN
PROJECT CHILD EXACTLY-ONCE CLEANUP: NEEDS_MORE_STATIC_PROOF
POST-SETUP SEAM: NEEDS_MORE_STATIC_PROOF
JMCS INTEGRATION DESIGN: NOT READY
JMCS NO-OP TEST: NOT READY
EXTERNALDISPLAY LIVE RENDER TEST: NOT READY
TYPE111 LIVE WORK: NOT READY
LD_PRELOAD STATUS: PARKED
BIGGEST BLOCKER: Honda has no proven supported lifecycle subscription point for a project-owned child across all receiver-session teardown sources.
```

## 12. Next action

Recover whether the existing `AirPlayReceiverSessionPlatformControl` callback's contract supports teardown observation and whether it can be extended through a documented, non-hook integration path; otherwise keep `PROJECT_CHILD_ATTACHMENT_POINT` unknown and design only a synthetic adapter boundary.
