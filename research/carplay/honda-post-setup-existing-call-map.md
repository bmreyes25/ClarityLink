# Honda post-Setup existing-call map — Step 43M

Evidence source: `extracted/system/system/bin/jmcs`, SHA-256 `cbc7ba881648fb8ffdfcc4c1100a028345c37134a2ae3b9dff7d76572851c232`. All code locations below were re-disassembled for 43M.

## Successful Setup caller path

`_connectionHandleMessage` begins at `0x28a30c` (Thumb). The caller's HTTP connection is held in `r4`, HTTP request/message in `r6`, session-bearing connection context in `r10`, Setup request dictionary at `[sp+0x1c]`, responseOut at `[sp+0x54]`, and status/result at `[sp+0x50]`.

| VA | Instruction/call | Transaction data and edge |
|---|---|---|
| `0x28af6a–0x28af70` | `r1=[sp+0x1c]`; `r0=[r10+0xf4]`; `r2=sp+0x54` | request/session/output-pointer args staged |
| `0x28af72` | direct Thumb `BL AirPlayReceiverSessionSetup` (`0x2854e0`) | only direct caller found; nonzero return branches to `0x28b040` |
| `0x28af76–0x28af7c` | save/check `r0` | stock success is zero; failure skips project response work |
| `0x28af7e–0x28af90` | Honda success metadata and session byte stores | same session remains recoverable through `r10` |
| `0x28af94–0x28afac` | stage `CFObjectSetProperty` args | success-only Honda metadata/property operation |
| `0x28afae` | direct Thumb `BL CFObjectSetProperty` (`0x2928d0`) | request/session/response/status remain live in caller frame; response has not been serialized |
| `0x28afb2–0x28afb8` | stage serializer args: `r0=r4`, `r1=r6`, `r2=[sp+0x54]`, `r3=sp+0x50` | exact connection, message, response, statusOut |
| `0x28afba` | direct Thumb `BL _requestSendPlistResponse` (`0x289f60`) | local synchronous plist serialization/body installation begins |
| `0x28afbe` | `r6=r0` | returned HTTP status saved; success requires `r0==0xc8` and `[sp+0x50]==0` |
| `0x28b048` | direct `BL CFRelease` on `[sp+0x1c]` | request dictionary release |
| `0x28b052` | direct `BL CFRelease` on `[sp+0x54]` | response dictionary release; graph lifetime ends |
| `0x28b790` | direct `BL HTTPConnectionSendResponse` | later send/commit; called after handler cleanup, so not a response-mutation seam |

All values are `HONDA_CONFIRMED` for this ELF's caller dataflow. Stack offsets are relative to `_connectionHandleMessage`'s unchanged frame at the candidate callsites.

## Calls until the response graph is released

The successful path has these calls after `AirPlayReceiverSessionSetup` returns and before `CFRelease(response)`:

| Callsite | Target | Linkage | Arguments/return and lifetimes | Other direct callers / scope |
|---|---|---|---|---|
| `0x28afae` | `CFObjectSetProperty` `0x2928d0` | internal direct Thumb BL | 7-argument AAPCS call (`object, queue, function, flags, property, qualifier, value`; first four in `r0-r3`, remaining on stack); OSStatus return is not tested by this caller. Request/session/response/connection/message/status remain reachable from caller frame. | 11 callsites including generic CF property helpers and unrelated Honda operations; function-prologue hook would be too broad. Exact site is Setup-success-only. |
| `0x28afba` | `_requestSendPlistResponse` `0x289f60` | internal direct Thumb BL to local `.symtab` function | `r0=connection`, `r1=HTTP message`, `r2=response`, `r3=&statusOut`; returns HTTP status. Before serialization, response is mutable. Request dictionary and session remain in caller frame but are not function args. | 4 callers: `0x28a19c`, `0x28afba`, `0x28b42a`, `0x28b54e`; generic HTTP plist response scope at function level. |
| `0x28afba` nested | `HTTPHeader_InitResponse` `0x29dccc` | internal direct BL | called before plist serialization; nonzero status takes 500 helper exit. The response graph remains an argument to caller's helper. | one direct caller in `_requestSendPlistResponse` |
| `0x28afba` nested | `CFPropertyListCreateData` `0x28e6fc` | internal direct BL | receives response graph in `r1`, binary-plist format `0xc8`, returns CFData or null. | 2 callers (`0x285158`, `0x289fb2`) |
| serializer nested | `CFDataGetBytePtr` `0x28e3dc`; `CFDataGetLength` `0x28e3ca` | internal direct BLs | extract data pointer/length; data lives until body setter completes | each has the serializer path as the observed direct caller |
| serializer nested | `HTTPMessageSetBody` `0x29d01c` | internal direct BL | `r0=HTTPMessage`, `r1=content type`, `r2=bytes`, `r3=length`; zero means body install success. It copies bytes into HTTP message storage. | 4 callers (`0x285180`, `0x289fdc`, `0x28a784`, `0x28b32a`); HTTP-message scope |
| serializer nested | `CFRelease` `0x28e312` | internal direct BL | releases temporary CFData before return; response graph is read-only consumed and not retained by this helper | widely used; generic |
| `0x28b04a`, `0x28b052` | `CFRelease` `0x28e312` | internal direct BLs | release request and response references on common cleanup | widespread |

The caller's serializer predicate is exactly `r0 == 0xc8` **and** `statusOut == 0`; successful body installation does not prove HTTP queue acceptance or peer receipt. Later `HTTPConnectionSendResponse` at `0x28b790` is a separate commit/send stage.

## Candidate scope summary

| Candidate | Scope / data visibility | Timing and decision |
|---|---|---|
| `CFObjectSetProperty` function | 11 calls across unrelated CF property operations; no exact Setup discriminator at function ABI | Broad prologue interception is rejected. Exact callsite `0x28afae` is narrow but occurs before serializer result is known. |
| `_requestSendPlistResponse` function | 4 direct HTTP callers; args provide connection/message/response/statusOut; connection→`+8` private context→`+0xf4` session is statically confirmed via `_connectionFinalize`, but exact parsed Setup dictionary is not an argument | Function prologue could be made semantic by HTTP request inspection, but no supported dynamic wrapper route exists and caller identity would be broader. |
| `CFPropertyListCreateData` | 2 users; receives response graph only | Too low-level and cross-traffic; no request/session/connection args; inside serializer. |
| `HTTPMessageSetBody` | 4 HTTP callers; message and serialized bytes only | After serialization, too late for response graph mutation; no session argument. |
| `HTTPConnectionSendResponse` | one direct callsite in common handler response path | Response graph has already been released; too late to append; nonzero commit result is returned to state machine. |
| Existing `AirPlayReceiverSessionSetup` call | one direct callsite at `0x28af72`; request/session/output pointer available | Runs before Honda caller's success metadata/property work. Cannot observe final serializer result without a later wrapper. |

The preferred seam is therefore the exact existing serializer callsite `0x28afba`: one site, successful Setup branch, all caller locals remain in the frame, response still mutable, and it can bracket the original serializer with pre/post project-only transaction logic. Replacing that `BL` requires a trampoline; it is not ordinary symbol interposition.
