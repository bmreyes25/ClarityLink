# Honda HTTP commit and failure lifecycle — Step 43H

**Artifact:** `extracted/system/system/bin/jmcs`, SHA-256 `cbc7ba881648fb8ffdfcc4c1100a028345c37134a2ae3b9dff7d76572851c232`. All conclusions are offline instruction-level findings. See [43H report](../../step-reports/43h-http-commit-and-session-cleanup.md).

## Response path and commit failure

`_requestSendPlistResponse` (`0x289f60`) initializes status 200 at `0x289f8e`, serializes the plist synchronously (`CFPropertyListCreateData`, `0x289fb2`), attaches bytes through `HTTPMessageSetBody` (`0x29d01c`, `0x289fdc`), releases temporary CFData (`0x289fee`), and returns HTTP status 200 or 500. `_connectionHandleMessage` retains its handler return in `r6` (`0x28afbe`) and builds the HTTP response headers. Header initialization and `HTTPHeader_SetField` errors branch to its common return at `0x28b798`; they are not reported as a successful send.

On the response path, the call at `0x28b790` invokes `HTTPConnectionSendResponse` and immediately branches to the common function epilogue. The call's `r0` status is not overwritten; `_connectionHandleMessage` returns it. `HTTPConnectionSendResponse` (`0x29dbe4`) calls `HTTPHeader_Commit` (`0x29dd18`). A nonzero result returns before the send state fields are written. In the common audited path, `HTTPHeader_Commit` returns the existing nonzero committed marker when already committed, `-6745` for an empty header, and `-6751` when adding the final CRLF would reach/exceed its 0x2000-byte header limit. The successful path appends CRLF and records its committed marker.

The state machine calls the request/message handler indirectly through `[connection+0x28]` (`0x29d6ea`). It checks the callback's returned `r0`; zero restarts the machine, nonzero enters `HTTPConnectionStop` plus the close callback (`0x29d752–0x29d75e`). Server-accepted connections install `_HTTPServerCloseConnection` (`0x29d798`) at that callback slot. Therefore the nonzero HTTP commit result is propagated to the state machine and takes the close path; it is not ignored or retried there.

| Failure site | Return/effect | Immediate caller | Connection effect | Session effect | Confidence |
|---|---|---|---|---|---|
| Plist creation returns null | HTTP 500 from serializer helper | `_connectionHandleMessage` | Sends error response if its headers/commit succeed | No direct teardown from serializer error | HONDA_CONFIRMED |
| `HTTPMessageSetBody` error | HTTP 500; helper also returns body error through output | `_connectionHandleMessage` | Error response path; its own header setup can fail | No direct teardown edge | HONDA_CONFIRMED |
| Response header init / `HTTPHeader_SetField` error | Nonzero handler return | `_HTTPConnectionRunStateMachine` | Stop + registered close callback | Finalizer reaches teardown if context has session | HONDA_CONFIRMED |
| Header empty/too long/already committed | `HTTPHeader_Commit` returns nonzero; `HTTPConnectionSendResponse` returns it unchanged | handler returns it; state machine tests it | Stop + close callback | Finalizer conditionally tears down session | HONDA_CONFIRMED |
| `SocketWriteData` returns terminal error | Nonzero state-machine result | `_HTTPConnectionRunStateMachine` | Stop + close callback | Finalizer conditionally tears down session | HONDA_CONFIRMED |

## Send state and socket states

`HTTPConnectionSendResponse` does no socket I/O and does not allocate in its body. After successful commit it fills connection-context iovec state from the HTTP response header/body pointers, sets the iovec count, then sets connection state `[connection+0xc0] = 1`. The next state-machine iteration uses `SocketWriteData`. No separate enqueue/list operation was found at this call site; the state transition occurs in the active state-machine callback. The message/header/body remain in the connection context; no response-message retain/copy operation is visible in this function.

| State | Operation | Success next | Retry/partial next | Terminal failure next | Confidence |
|---|---|---|---|---|---|
| 0 | `HTTPMessageReadMessage`; then handler `[connection+0x28]` | Handler returns 0; loop rechecks state | status 11 yields/suspends source path | other status or handler nonzero -> stop and close callback | HONDA_CONFIRMED |
| 1 | `SocketWriteData` on prepared iovec | all vectors consumed -> reset messages if keep-alive flag is set, restore state 0 | status 11 returns through dispatch-source resume/yield; partial `writev` updates iovec and returns status 11 | other status -> stop and close callback | HONDA_CONFIRMED |

`SocketWriteData` retries `EINTR` (`errno == 4`). Positive `writev` results are passed to `UpdateIOVec`; fully consumed vectors return 0, while remaining vectors update base/length/count and return 11, which the state machine treats as retry. `EAGAIN`/would-block also returns 11. Other errors propagate. The disassembly does not distinguish every possible errno by meaning beyond the explicit EINTR and 11 checks.

## Connection and parent session

`_connectionFinalize` (`0x289d90`) reads a per-connection context through `[connection+8]`. If context `[+0xf4]` is non-null, it calls `AirPlayReceiverSessionTearDown(session, NULL, reason, NULL)` (`0x289dc6`), releases that session reference, and clears `[+0xf4]`. This proves the connection-context-to-session edge and conditional finalizer cleanup. It does not prove every HTTP connection has a session, whether multiple connections can share one session, or that all session termination is caused by HTTP connection destruction.

The Type110 Screen listener/worker is stored in the AirPlay session's screen fields and `_ScreenTearDown` (`0x284628`) sends stop command 0x71, joins its worker if started, closes the session screen descriptor when nonnegative, writes `-1`, and clears its started byte. This is distinct from the HTTP control connection fd. It does not prove that accepted ScreenStream TCP sockets share HTTP lifetime; their exact relationship is UNKNOWN.

## Receiver-session teardown ordering

`AirPlayReceiverSessionTearDown` (`0x2852ec`) first calls `AirPlayReceiverSessionPlatformControl` (`0x285364`). With a null params dictionary (the `_connectionFinalize` call), it takes the full teardown path: log end/reset a session flag, `_ScreenTearDown`, `_TearDownStream` for the two audio/control stream slots, `_ControlTearDown`, `_TimingFinalize`, clock finalization, then cancellation/release/clear of the session dispatch source. `_TearDownStream` (`0x284bd8`) signals and joins an active worker, closes both nonnegative descriptors and sets them to -1, frees jitter/ring buffers, and clears stream state. `_ScreenTearDown` has negative-fd and started-byte guards; no single session-wide “already torn down” guard is visible. `_connectionFinalize` releases the session after the call.

Some non-null partial teardown requests iterate requested stream dictionaries and handle types 100/101/110, with the Type110 branch scheduling deferred work. That is distinct from the full null-params path above. No crypto-zeroization claim is made from this bounded trace.

| Operation | Evidence / order | Confidence |
|---|---|---|
| Platform-control call | First teardown-side call before examining requested streams | HONDA_CONFIRMED; not proven to be a project lifecycle notification API |
| Stop/join screen worker and close screen descriptor | Full teardown calls `_ScreenTearDown`; descriptor guard then reset to -1 | HONDA_CONFIRMED |
| Stop/join stream workers, close stream descriptors, free buffers | Full teardown calls `_TearDownStream` twice for session stream slots | HONDA_CONFIRMED |
| Control/timing/clock cleanup | `_ControlTearDown`, `_TimingFinalize`, `AirTunesClock_Finalize` in sequence | HONDA_CONFIRMED |
| Cancel/release session dispatch source | Last resource step before returning | HONDA_CONFIRMED |
| Session release | Caller `_connectionFinalize` releases and clears context pointer after TearDown returns | HONDA_CONFIRMED |
| Accepted ScreenStream socket closure / crypto zeroization | Not established by this bounded path | UNKNOWN |

## Child attachment assessment

| Candidate | Normal teardown | Network failure | Setup failure | Parent live at event | Integration evidence |
|---|---|---|---|---|---|
| Wrap/call around `AirPlayReceiverSessionTearDown` | Covers callers that execute it | Covers finalizer path when context session exists | Not shown for pre-session Setup failure | Yes at function entry, but lifecycle callback API not exposed | Function is internal; attaching requires an unproven integration point |
| `AirPlayReceiverSessionPlatformControl` callback | Called at teardown entry | Indirectly, because teardown calls it | Not proven | Session is passed into call | It is an existing callback path, but teardown-specific project notification semantics/API are not established |
| `_connectionFinalize` | Connection destruction only | Covers terminal HTTP connection close with nonnull context session | Not all Setup failures | Session pointer is live before TearDown | Internal and HTTP-connection-specific; misses other parent teardown sources |
| `_ScreenTearDown` | Screen child teardown only | Reached by full session teardown | Not all failures | Parent is live | Internal Type110 path; unsuitable as general child owner |
| Session delegate/platform lifecycle | Potential candidate | Unknown | Unknown | Unknown | No dedicated project-child lifecycle callback recovered |

`PROJECT_CHILD_ATTACHMENT_POINT: UNKNOWN`. Static evidence proves Honda's parent teardown edge, not a supported way for a project component to subscribe to every teardown. A future integration design must introduce/prove that attachment separately; it must not assume the HTTP connection is identical to ScreenStream lifetime.

## 43G note superseded

Step 43G correctly identified the untested return at `HTTPConnectionSendResponse` but left its effect unknown. Step 43H follows the return through `_connectionHandleMessage` and `_HTTPConnectionRunStateMachine`: commit failure is returned by the callback and takes the connection close path. Session teardown is then conditional on the finalizer's nonnull context session pointer.
