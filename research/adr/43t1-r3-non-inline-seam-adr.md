# ADR 43T1-R3 — no evidenced safe non-inline mediation seam

- **Status:** Accepted for current evidence; revisit only when new static evidence identifies a supported extension point.
- **Date:** 2026-10-03
- **Scope:** Offline architecture decision. No Honda contact, ADB, vehicle connection, RAM attachment, listener, Type111 negotiation, or runtime write.

## Context

R2 rejected the current four-byte Thumb inline patch seam: it crosses the modeled fetch-group boundary, both halfword store orders expose mixed instruction states, cache synchronization does not establish atomicity, and thread stop/rendezvous plus independent restoration are unproven. The question for R3 was whether an existing control-flow, wrapper, callback, dispatch, serializer-adjacent, listener-adjacent, or lifecycle seam can mediate Type111 Setup without patching that callsite.

Historical static evidence identifies a valuable Setup response interval in `_connectionHandleMessage`: stock Setup succeeds, Honda response metadata is added, the response object is passed to `_requestSendPlistResponse`, and its local serializer/body result is checked. But the serializer call is a direct internal Thumb BL at `0x28afba`. The helper is local and absent from `.dynsym`; no relevant PLT/GOT route or existing wrapper is found. The 43M wrapper is an offline model. Its exact caller-frame context can only be used by redirecting the direct call.

Recovered callback tables are Honda-owned fixed records with replacement semantics: session delegate is copied as 11 words; app event callback is a global 24-byte record; proxy screen callback is a singleton 24-byte record. No multi-subscriber extension or safe chain is established. The finalizer is a real static cleanup path, but project-child subscription is absent, event identity/coverage is insufficient, and it cannot establish cleanup for every failure. Loader and proxy audits found no supported plugin route. External transport mediation is rejected because it would risk CarPlay authentication/transport and requires forbidden injection/MITM/persistent changes.

## Decision

**Reject runtime interposition for now.** Continue only offline prior-art and static evidence research. Do not add host model code: no candidate seam meets the threshold for offline modeling as an existing non-inline integration point. The current decision is `ABANDON_RUNTIME_INTERPOSITION_UNTIL_NEW EVIDENCE`.

## Consequences

- The response-path wrapper remains a useful `MODEL_ONLY` transaction contract, not an existing Honda wrapper.
- The serializer boundary is retained in documentation as static control-flow context, not a callable seam.
- Honda callbacks/finalizers remain untouched; fixed callback replacement is not treated as extensibility.
- No Type111 or Type110 compatibility claim is promoted. Type111 schema, acceptance, and security remain unknown; Type110 behavior remains stock-owned.
- No RAM experiment review is justified. Project recommendation: `NO_GO`.
- Reopen only if a preserved artifact/source proves a non-destructive supported call/registration/load mechanism, bounded object ownership and cleanup, and restoration without the rejected inline patch.

## Rejected alternatives

1. **Pivot to exact serializer wrapper:** needs the direct callsite trampoline; rejected by R2 mixed-state/quiescence/restoration evidence.
2. **Pivot to callback/dispatch replacement:** overwrites Honda-owned singleton/fixed records and can displace stock handling; no subscriber mechanism is shown.
3. **Use PlatformFinalize as project cleanup owner:** no project subscription; finalizer coverage is incomplete and callback event does not carry session identity.
4. **Use proxy callback registration:** second registration is rejected and table is singleton; replacing it risks stock Type110 screen behavior and does not mediate Setup.
5. **Use preload/wrapper/plugin load:** no existing controlled load point is evidenced; startup changes and rollback are unbounded.
6. **External process/proxy:** no compliant transparent route found; transport/authentication and forbidden injection/MITM risks make it unsuitable.

## Safety rationale

Every known response-mutation-capable point requires executable redirection; every callback candidate either has no relevant Setup context or is a replacement slot owned by Honda; every lifecycle signal is insufficient as a project resource owner. Because neither entry nor independent restoration is established, adding synthetic code would imply a seam that does not exist in reviewed evidence. Leaving runtime interposition disabled is the only supported conclusion. This ADR does not authorize any car experiment.
