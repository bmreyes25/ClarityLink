# ADR 43T1-R3C — Honda session-addressable integration

- **Status:** Accepted
- **Date:** 2026-10-03
- **Decision:** `RUNTIME_INTERPOSITION_ARCHITECTURE_EXHAUSTED`
- **Project recommendation:** `PIVOT_AWAY_FROM_HONDA_RUNTIME_INTERPOSITION`

## Context

R2 rejected inline instruction patching. R3A found no supported non-inline Setup mediation seam and kept lifecycle ownership as one bounded static question. R3B found no project-child association, additive cleanup subscription, or stable generation identity. R3C searched the preserved Honda evidence for context/user-data slots, observers, registrations, callback chains, session registries, stable IDs, and a paired Setup/cleanup path.

This decision is bounded to reviewed preserved artifacts and callsites; it is not a universal claim about unrecovered firmware.

## Decision

No supported session-addressable Honda runtime integration path is evidenced. Stop pursuing Honda `jmcs` runtime interposition under the current architecture. Pivot to offline modeling and non-Honda-dependent work. Reopen only if new static evidence demonstrates an additive entry, stable session identity, Setup visibility, same-identity cleanup, and no rejected mutation.

## Candidate assessment

- **Strongest candidate:** Honda's own `AirPlayReceiverSessionRef` appears both at internal Setup and in the Honda finalizer. It fails as an extension because no non-replacement subscriber can observe both sites; its generation/non-reuse guarantee is unknown; the installed delegate is a Honda-owned full-record copy.
- **Setup side:** Setup has a real mutable response dictionary and stock `_AddResponseStream` array append before synchronous serialization. That is internal transaction state, not a supported project entry. The serializer call is a direct internal call with no wrapper route; redirecting it returns to the rejected patch/interposition category.
- **Cleanup side:** CF `_Finalize` calls Honda's installed per-session callback then `PlatformFinalize`. The callback is Honda-owned. The separate global destroy event loses the session pointer. Connection teardown is conditional and its known stream parser skips unknown Type111.
- **Identity:** Raw session pointer is present internally at Setup/finalize. No Honda generation value, pointer non-reuse guarantee, UUID, or numeric session ID contract was recovered. `streamConnectionID` is a Type110 stream input without a recovered same-session cleanup lookup or reuse guarantee.
- **Ownership:** Honda owns session/context, delegate records, platform context, response graph, and Type110 resources. CF containers can hold/appended data, but this is not an observer list or project property bag. No project child registry integration is evidenced.
- **Registration semantics:** Session/server delegates are copied wholesale; the global interface event callback is one 24-byte slot; the proxy screen callback is singleton. No append-only registration exists in reviewed evidence.
- **Runtime mutation:** A usable entry would require callback replacement or a rejected control-flow redirect. Both are disallowed. Unknown struct fields cannot be treated as free storage.
- **Type110:** No safe project route can establish Type110 preservation in Honda at runtime. Stock Type110 handling remains Honda-owned; Type111 teardown is not implied by Type110 ownership.

## Alternatives rejected

Inline patching, arbitrary overwrite, callback/table/vtable/function-pointer replacement, global callback replacement, ptrace or process-memory writes, root/persistence, APK installation, linker/preload mutation, device/USB/network injection, and manual phone traffic manipulation remain `REJECT_UNSAFE` under the project boundary. An offline sidecar model is not an integration path and is not recommended as R3D runtime work.

## Consequences and remaining unknowns

No Honda runtime experiment, listener, Type111 negotiation, or interposer model is justified. The bounded unanswered question is whether some **newly recovered Honda artifact** contains a supported additive extension interface not present in the reviewed evidence. Until such evidence is provided, repeated search of the same paths is not a useful next milestone. Type111 compatibility, phone acceptance, and media behavior remain unknown but cannot be addressed by this architecture.

## Evidence

See [session-addressable audit](../runtime/43t1-r3c-session-addressable-extension-audit.md), [registration audit](../runtime/43t1-r3c-registration-and-observer-audit.md), [identity map](../runtime/43t1-r3c-session-identity-map.md), [entry/cleanup pairing](../runtime/43t1-r3c-entry-cleanup-pairing.md), R2/R3A/R3B step reports, and their linked hash-matched static inventories.
