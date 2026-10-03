# 43T1-R1 future experiment checklist — design only

**Status: NOT AUTHORIZED / NOT EXECUTABLE.** This checklist is a proposal for a later separately reviewed parked session. Completing this page does not grant permission to contact or modify Honda.

## Goal

Observe whether one preapproved, four-byte Thumb callsite RAM-only substitution can be installed, independently verified, then restored to the exact stock bytes while preserving receiver identity and normal stock UI/audio/cluster. No Type111 decoder, cryptographic mode, cluster rendering, or media path.

## Hard prerequisites before a future session

- Separate ECC review and explicit user authorization for that session.
- Honda parked/stationary; user confirms normal head unit, display, audio, cluster, intended car, and required connection state.
- A tested independent recovery/stop plan exists for receiver crash, host loss, transport loss, and power interruption.
- Exact Honda identity, firmware hash, ELF hash, runtime mapping/load bias, callsite address, expected original bytes, decoded instruction/target/continuation, permissions and alignment are freshly verified. Static preferred VA alone is insufficient.
- API-17 ARM/Bionic mechanism, permissions, cache synchronization and thread quiescence are validated in a compatible lab setup. No API-22+ behavior substituted.
- Honda CFLite constructor callbacks/getter ownership and all bridge boundary lifetimes are established.
- No wildcard bind; an observed interface/address/family/scope/route policy has been independently reviewed for the present process/network phase.
- Independent observer/verifier and exact write/audit accounting are ready before the first write.
- All failures in the matrix have a feasible recovery; any UNKNOWN recovery path blocks start.

## Proposed limits

- Target memory writes: **maximum 2 total**: one four-byte RAM-only install attempt and one four-byte exact restoration attempt. No third write, retry, instruction rewrite, listener write, persistent file, APK, or system/boot/storage write.
- Listener: at most one generation and one specific address; at most one phone connection; no wildcard.
- Stock serializer: exactly one call on the one observed transaction.
- Runtime: hard stop at **5 seconds** from attachment attempt; this is a proposed cap, not a Honda timing claim. If time accounting cannot be independently enforced, do not start.
- Prefix observation: **0 bytes** in the first attach/restoration-only experiment. Type111 negotiation and listener are out of scope.
- Any timeout, partial write, permission/cache error, thread-set change, unexpected target state, user abort, or lost host ends activity. Do not retry during the session.

The two-write budget is viable only if pre-session lab proof shows the entire restore operation is safe for all possible result states of the single install attempt. The current Honda callsite crosses a 4-byte fetch group and no single atomic full-instruction store is established; **this prerequisite currently fails**. Thus the checklist is not presently executable.

**R2 clarification:** The host-only two-halfword model enumerates mixed instruction states for either store order. Alignment alone does not remove the partial-write states. Until an API-17-compatible all-thread stop/re-entry protocol and independent recovery are demonstrated, the proposed write budget is not evidence of viability. Treat any downstream checklist text suggesting otherwise as superseded by this explicit stop condition.

## Sequence and success criteria

1. Verify normal stock state and exact process/image identity; no stale address reuse.
2. Capture independent original memory readback: exact address, alignment, bytes, hash, decoded Thumb sequence, branch target and continuation.
3. Confirm no thread PC is in or can race through the replacement span using a validated API-17 ARM mechanism; any uncertainty aborts before a write.
4. Stage the replacement and all project-owned state privately; Type110 remains untouched. No listener is created.
5. Record a single install attempt. Read back candidate bytes, hash, instruction sequence, expected target, page permissions, and cache-sync completion independently. Any mismatch aborts to the single bounded restoration attempt only if the exact observed state is a prevalidated restorable form.
6. Restore once, with compare-before-restore against the exact candidate form. Do not overwrite foreign/partial bytes.
7. Independent verifier reads the same exact span and context; two separated observations must match exact original address, bytes, SHA-256, alignment, instruction sequence, branch target/continuation, mapping identity, and resource absence.
8. Detach and confirm the target process remains the same epoch or was restarted. Record the distinction.
9. User confirms stock Center Display Audio, audio and cluster are normal. If process restarted, treat this as a new process and revalidate identity before interpreting any addresses.

## Failure criteria

Any precondition absent, identity or mapping changes, callsite mismatch, inability to rendezvous threads, write count uncertainty, partial/foreign bytes, cache/protection failure, verifier mismatch, unexpected CF ownership, stale generation, listener wildcard, serializer count other than one, stock return change, timeout, disconnect, physical symptom or user abort is failure. Do not translate failure to “probably restored.”

## Rollback and independent verification

Rollback order is in [the state machine](43t1-r1-runtime-state-machine.md). One exact restoration attempt only. If it fails or state is ambiguous: report UNKNOWN, stop further target operations, preserve all available evidence, and request a separately reviewed recovery procedure. Reboot may be part of recovery but is never itself proof of stock operation.

## Required user confirmations

Immediately before any future target contact: parked/stationary, normal powered head unit, intended Honda, established reviewed connection, expected cable/display/audio/cluster state. During a later separately approved UI transaction the user must confirm the expected screen/audio/cluster state before each phase. This R1 document authorizes no such prompts or action.

## Exact CAR OFF point

For a future approved run, the instant the one target-side attempt exits or any stop condition occurs: state **“CAR MAY BE TURNED OFF NOW. No further Honda or ADB commands will be used in this milestone.”** Then issue no more Honda/ADB commands and continue only offline. This R1 work itself has not contacted Honda, used ADB, or required a CAR-OFF boundary.
