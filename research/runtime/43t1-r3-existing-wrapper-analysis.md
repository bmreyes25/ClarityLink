# 43T1-R3 — existing wrapper analysis

## Questions and answers

### Was there an actual existing wrapper?

No. `43M` examined the hash-matched `jmcs` and found the Setup serializer call at `0x28afba` is a direct internal Thumb `BL` to local `.symtab` function `_requestSendPlistResponse` (`0x289f60`), absent from `.dynsym`; no relevant PLT/JUMP_SLOT route exists. The function has four direct callers. The separate Python wrapper contract in 43M is an offline synthetic model, not an existing Honda wrapper (`MODEL_ONLY`).

### Is it callable without inline patching?

No supported route is evidenced. Normal ELF interposition cannot see this internal direct call. The exact Setup-only context resides in `_connectionHandleMessage`'s live caller frame; a future 43M trampoline there requires changing the callsite. R2 later establishes that the separate Setup BL at `0x28af72` straddles the modeled four-byte fetch group and that both halfword patch orders can produce mixed instruction states. It returns `INLINE_PATCH_REQUIRES_UNPROVEN_THREAD_STOP_AND_REMAINS_NO_GO`. No callback/dispatch entry has been shown to redirect this call non-destructively.

### Does it already own response mutation?

The Honda handler owns response construction and passes its mutable response object to the serializer. The serializer reads that graph to produce a binary plist. No existing project or third-party wrapper mutation is evidenced. `MODEL_ONLY` response append rules are not Honda behavior.

### Does it call the serializer?

The Honda `_requestSendPlistResponse` helper synchronously calls `CFPropertyListCreateData` with format `0xc8`, reads CFData bytes/length, and calls `HTTPMessageSetBody`; it returns local HTTP/body status. That is `HONDA_CONFIRMED` static flow. It does not prove HTTP delivery or phone receipt. A hypothetical wrapper around this helper would call the original serializer once by contract, but no such wrapper exists.

### Can it be modeled as a non-inline transaction?

Yes as an offline interface contract (`MODEL_ONLY`): prepare transaction before the final graph mutation, invoke stock serializer once, observe the exact result/status, and commit or roll back project-owned resources. That model is useful for reasoning but does not create a natural Honda entry point. This R3 adds no model because its purpose is to establish an existing non-inline entry and none meets that condition.

## Exact supporting evidence

- `research/carplay/honda-post-setup-existing-call-map.md`: Setup at `0x28af72`; success-only metadata; exact serializer arguments staged at `0x28afb2–0x28afb8`; direct call at `0x28afba`; result saved at `0x28afbe`; request/response released at `0x28b048`/`0x28b052`; later send at `0x28b790`.
- `research/carplay/honda-request-send-plist-wrapper-audit.md`: `_requestSendPlistResponse` is local, four direct callers, no PLT/GOT route; serializer/body behavior and distinction between caller frame and function arguments.
- `step-reports/43m-existing-call-wrapper-seam.md`: exact candidate, caller-set inventory, and explicit requirement for callsite trampoline.
- `step-reports/43l-post-setup-transaction-seam.md`: response lifetime and mutation/serializer window; helper-callout safety partial.
- `step-reports/43l1-callout-safety-cleanup-reachability.md` and `43l2-session-finalizer-extension-audit.md`: no safe callout or non-destructive cleanup subscription established.
- `step-reports/43t1-r2-api17-arm-bionic-cflite-readiness.md`: inline mixed-state model and unresolved stop-world/restoration.

## Unknowns and limits

`UNKNOWN`: whether an unexamined proprietary dynamic mechanism outside preserved artifacts exists; Honda-specific runtime callability; function-pointer re-entry/concurrency; API/loader policy in the actual running system; callback lifecycle coverage; serializer failure behavior beyond recovered static branches; project cleanup ownership after send/session failures; Honda Type111 acceptance/security. No claim of absence is made beyond the reviewed binary and static artifacts. Apple CF references, AOSP generic loader documentation, synthetic tests, and external prior art are not Honda proof.

**Conclusion:** no existing wrapper is callable as a non-inline transaction on current evidence. Keep the wrapper contract as offline reasoning only; reject its trampoline attachment as unsafe under the R2 boundary.
