# Honda project-child lifecycle contract — Step 43J

**Scope:** offline static analysis and synthetic design only. Honda evidence is tied to `extracted/system/system/bin/jmcs`, SHA-256 `cbc7ba881648fb8ffdfcc4c1100a028345c37134a2ae3b9dff7d76572851c232`. No binary or vehicle changes.

## Honda routing findings

`AirPlayReceiverSessionPlatformControl` at `0x28cd88` compares the command string. On the `tearDownStreams` branch it extracts the `streams` array, reads each dictionary's `type`, handles 100/101/110, logs and skips unknown types, then performs internal stream update/teardown work. It does not load/call the session delegate control function at `session+0x24` on this branch. The `session+0x24` indirect callback call is in the other-command path at `0x28d2c2–0x28d2d6`. Thus application control cannot see this command through that path. Type111 takes the unknown-type path; it is ignored by the typed parser, not supported and not sent to application control.

The delegate table at `session+0x14` has an exact 44-byte structural slot/population match to pinned R11B's 11-word table. This is only an external structural fingerprint; it does not establish Honda source names or provenance.

`_Finalize` at `0x284d24` directly calls `AirPlayReceiverSessionPlatformFinalize` once at `0x284d3e`. That helper at `0x28cd60` tolerates a null platform pointer (`session+0x10`), stops HID, calls `_TearDownStreams(session, NULL)`, frees platform state, and clears `session+0x10`. It has one statically found caller, the CF runtime finalizer. It is a full-session cleanup signal independent of HTTP state or earlier stream teardown. The session pointer is live as the finalizer's argument during the call. Once-per-CF-finalization is proven at the direct call-site level; unusual runtime reentrancy is outside static evidence.

## External ClarityLink registry contract (synthetic)

Keep `ProjectSessionRegistry[AirPlayReceiverSessionRef] -> ChildState` wholly external to Honda-owned memory. ChildState contains generation, listener, accepted socket, crypto/parser/decoder/renderer state, and a stopped flag. Do not alter the Honda delegate/context/context2, platform pointer, Type110 structures, crypto state, or audio state.

| Event | Project behavior | Honda behavior |
|---|---|---|
| Successful post-Setup project allocation | Register child | Stock Setup remains unchanged |
| Type110-only teardown | Keep child | Honda remains authoritative |
| Type111 teardown | Stop project child once | Observe original request unchanged; no Type111 support assumed |
| Combined 110+111 | Stop only project child | Honda keeps its Type110 handling |
| Missing stream list / whole-session teardown | Clean project child | Honda receives original request |
| PlatformFinalize | Idempotent child cleanup safety net | Call stock finalizer exactly once |
| suggestUI/showUI/stopUI/modesChanged/provider change | Preserve transport | UI state alone is not teardown |
| Partial init / missing child | No-op safely | Honda cleanup continues |

## Synthetic stock-delegating adapter contract

`project_platform_control(session, flags, command, qualifier, params, outParams)` inspects the command safely and observes only `tearDownStreams`; it leaves request and return code unchanged, never strips Type110, invokes stock PlatformControl exactly once, holds no locks across stock, and fails open if project observation fails. Type111 cleanup belongs only to project state.

`project_platform_finalize(session)` removes/stops any registered child exactly once, tolerates no child and cleanup errors, does not mutate Honda state, then invokes stock PlatformFinalize exactly once. No project failure may prevent Honda cleanup. This is a **synthetic design**, not proof that either Honda symbol is safely extensible or interposable.

## Safety and remaining boundary

The exact reason for session death is diagnostic rather than required for cleanup correctness if all project child state is keyed to the session and unconditional cleanup is attached to the proven finalization event. The project registry and child-stop semantics are ready for an offline prototype. Safe integration of PlatformControl/PlatformFinalize and post-Setup child creation remain unproven; no interposer or Type111 implementation is authorized by this research step.

Failure/concurrency cases to model: 110 only, 111 only, combined, duplicate 111, Type111 racing finalization, finalize without teardown, absent child, cleanup failure, unknown command/type, malformed array, UI/provider events, stock error, already-stopped child, and synthetic pointer-generation reuse. Assert stock is called once, request is immutable, Type110/audio state stays untouched, child resources release once, and finalization cannot leak child state.
