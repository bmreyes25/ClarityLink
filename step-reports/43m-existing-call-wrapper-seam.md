# Step 43M — existing-call wrapper seam (offline, 2026-10-01)

## Scope and baseline

Continued from clean `main` at `852b8ab658a1e8d609ba45aeed52713c414ce094`. The reference `extracted/system/system/bin/jmcs` SHA-256 matches `cbc7ba881648fb8ffdfcc4c1100a028345c37134a2ae3b9dff7d76572851c232`. The ELF was statically inspected only. No Honda execution, patching, deployment, listener, or live test occurred.

**Decision:** ordinary existing-function interposition is not supported by the observed call route. The narrowest useful integration strategy is **C — MINIMAL_VALIDATED_TRAMPOLINE**, replacing only the existing successful-Setup serializer call site at `0x28afba` in a future, separately reviewed offline design. This milestone implements only a synthetic wrapper contract and read-only compatibility planner; it does not emit patch bytes or modify the ELF.

## Successful Setup window

`_connectionHandleMessage` at `0x28a30c` is Thumb. It calls `AirPlayReceiverSessionSetup` by direct BL at `0x28af72` (`0x2854e0`), passing the session from `[r10+0xf4]`, request dictionary `[sp+0x1c]`, and response output `[sp+0x54]`. This is the only direct caller found. A nonzero Setup result branches to the stock failure path; zero falls through the Honda success metadata/property sequence, including `CFObjectSetProperty` at `0x28afae`.

At `0x28afba`, a direct internal Thumb BL calls `_requestSendPlistResponse` at `0x289f60` with `r0=connection (r4)`, `r1=HTTP message (r6)`, `r2=response ([sp+0x54])`, and `r3=&statusOut ([sp+0x50])`. The caller stores `r0` at `0x28afbe`; success is exactly `r0 == 0xc8 && statusOut == 0`. It releases the request and response at `0x28b04a` and `0x28b052`. `HTTPConnectionSendResponse` occurs later at `0x28b790`, after the response graph has been released. Full call and liveness details are in [the existing-call map](../research/carplay/honda-post-setup-existing-call-map.md).

## Candidate audit and linkage

| Candidate | Finding |
|---|---|
| `CFObjectSetProperty` (`0x2928d0`) | 11 direct callers across unrelated property operations. The exact Setup-success call at `0x28afae` is narrow but precedes serializer outcome. Function-level wrapper is too broad. |
| `_requestSendPlistResponse` (`0x289f60`) | Four direct internal callers. It receives connection/message/response/statusOut, not the parsed request or session. A static connection-private-state chain to session exists, but normal dynamic wrapping is not proven and function scope includes unrelated HTTP plist responses. |
| `CFPropertyListCreateData` (`0x28e6fc`) | Two callers; response only, too low-level and lacks transaction identity. |
| `HTTPMessageSetBody` (`0x29d01c`) | Four callers; sees serialized bytes after the mutable response graph has been consumed. |
| `HTTPConnectionSendResponse` (`0x29dbe4`) | One relevant handler call after response release; too late to extend the graph. |
| `AirPlayReceiverSessionSetup` (`0x2854e0`) | One direct caller and strong Setup identity, but occurs before Honda's success metadata and cannot observe serializer result alone. |

ELF inspection found no relevant PLT/JUMP_SLOT wrapper route for these calls. The successful-path calls are direct same-ELF Thumb BLs; `_requestSendPlistResponse` is local in `.symtab`. Global symbol visibility, where present for library helpers, would not prove Android runtime interposition. The exact Setup serializer callsite is therefore the only bounded seam that has the needed pre- and post-serializer context, but reaching it requires a future callsite trampoline. No runtime mechanism is selected here.

## Wrapper contract and preservation

The offline model in `src/claritylink-negotiation/wrapper_contract.py` specifies: project preparation and entry construction happen before mutation; stock serializer is called exactly once in every path; project failures before mutation fail open to the untouched stock response; any project-owned mutation is last; child commit requires the synthetic serializer predicate `(r0 == 0xc8 && statusOut == 0)` and a still-current generation; serializer failure rolls back project-owned resources while preserving Honda's returned result. It never dereferences opaque Honda pointers. The current Type110 object and audio state are outside project ownership and remain unchanged in the tests.

The caller frame at the exact site supplies opaque session identity, project generation correlation, request, response, connection, message, and status output without a process-global “current transaction”. The integration contract must use a generation registry, idempotent rollback, bounded leases, and a bounded nonblocking request-thread operation. Listener bind/listen and actual port discovery precede any future response `dataPort`; decoder startup, rendering, waits, and network reads belong on a project worker. Honda thread serialization and reentrancy are not statically established.

This model does not claim Type111 schema is Honda-confirmed. No Type111 mutation is implemented. If a future project extension fails before mutation, invoke the stock serializer with the original response. If serialization fails after an extension was appended, roll back project resources and let Honda's normal error path proceed; Type110 presence in memory does not prove successful delivery on that error path.

## Decision table

| Field | Result |
|---|---|
| EXISTING CALL WRAPPER | `EXISTING_CALL_WRAPPER_NOT_SUPPORTED` for ordinary function interposition; exact-callsite stock-delegating trampoline remains viable offline design |
| BEST TARGET | Existing `_requestSendPlistResponse` callsite in `_connectionHandleMessage` |
| TARGET ADDRESS | `0x28afba` |
| CALL SCOPE | `EXACT_SETUP_ONLY` at the selected site; function target is otherwise HTTP-global |
| DIRECT OR PLT | Direct internal Thumb BL; no PLT route |
| STOCK ORIGINAL CALL PRESERVED | Yes, contract requires exactly once |
| REQUEST AVAILABLE | Yes, caller frame `[sp+0x1c]` |
| RESPONSE AVAILABLE | Yes, argument `r2=[sp+0x54]` |
| SESSION IDENTITY AVAILABLE | Yes, caller frame via `[r10+0xf4]`, opaque and non-owning |
| RESPONSE MUTABLE AT ENTRY | Yes, before serializer call |
| SERIALIZER RESULT OBSERVABLE | Yes, after original returns: `r0==0xc8 && statusOut==0` |
| CALLER SET COMPLETE | Bounded candidate caller inventory: Setup `0x28afba`; serializer has four total callers |
| CONCURRENCY | Runtime concurrency unknown; generation-keyed/no-global-state model |
| GLOBAL STATE REQUIRED | No |
| CALLBACK REPLACEMENT REQUIRED | No |
| LD_PRELOAD REQUIRED | No; remains parked |
| INLINE TRAMPOLINE REQUIRED | Yes for this exact-callsite route; implementation not performed |
| TYPE110 PRESERVED | Yes by offline contract: stock response identity/data preserved absent explicit project extension |
| AUDIO PRESERVED | Yes by offline model: audio remains outside project-owned state |
| GENERATION GUARD COMPATIBLE | Yes, offline contract/model |
| HONDA RUNTIME PROOF REQUIRED | Yes before any runtime use |
| JMCS INTEGRATION DESIGN | `MINIMAL_TRAMPOLINE_REQUIRED_OFFLINE_DESIGN_NEXT` |
| LIVE TEST READY | No |
| TYPE111 LIVE READY | No |
| EXTERNALDISPLAY LIVE READY | No |
| LD_PRELOAD | `PARKED` |
| NEXT ACTION | Design and validate a synthetic stock-delegating Thumb callsite trampoline model for `0x28afba`, including ABI preservation, branch/continuation behavior, and fail-closed hash/byte gates; no Honda binary modification. |

## Future trampoline target (plan only)

The selected site is Thumb-2 BL bytes `fe f7 d1 ff`, targeting `0x289f60`, with continuation `0x28afbe`. One complete 4-byte instruction is the minimum displaced span; it is PC-relative and must be re-encoded to call the exact stock serializer once, or use a validated reachable veneer. The continuation must restore stock return/status semantics and caller register/stack invariants. Exact binary hash and call bytes are compatibility gates; mismatch must reject. Runtime mapping, installation, executable memory policy, instruction-cache handling, and activation remain unknown. See [minimal target plan](../research/carplay/honda-minimal-future-trampoline-target.md). No patch bytes are emitted.

## External prior art

`EXTERNAL_PRIOR_ART`: the MHI2 AltScreen hook map reports stock AirPlay delegation and validated ARM prologue/trampoline hooks where ordinary symbol interposition did not cover internal lifecycle calls. This motivates considering a narrow trampoline but does not establish Honda loader, ABI, instruction, or runtime facts. `EXTERNAL_PRIOR_ART`: current `carlink_linux` capability notes describe secondary-display capability signaling in the Setup response and a second display capability structure; this supports keeping the Honda post-Setup/pre-serialization region as the relevant design boundary, not any Honda Type111 field semantics.

## Verification and readiness

- Full configured suite: **287 passed, 4 skipped**. The four skipped tests require ignored/private capture fixtures and are excluded by the repository runner.
- Focused Setup, response delivery, project lifecycle, wrapper-contract, and callsite planner groups: **73 passed**; wrapper/planner pair after final planner correction: **16 passed**.
- Self-locator standard-library smoke: **3 passed**. Simulator contract adapter, dual-screen model, guidance expiry, and Type111 failure-twin checks all passed.
- `git diff --check`: **PASS**.
- No dedicated ECC review service was available in this environment; ECC engineering/review checklists were applied manually. JMCS implementation, vehicle test, Type111 live, and ExternalDisplay live remain NOT READY.
