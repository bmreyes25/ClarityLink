# Honda post-Setup integration contract — Step 43L audit target

**Status: `NEEDS_MORE_STATIC_PROOF`.** This checklist defines facts to recover from the offline, hash-matched Honda binary. It is not authorization or a design for loading, hooking, patching, or live integration.

The portable synthetic APIs are documented in [project-session-registry.md](project-session-registry.md). Honda's successful Setup caller has a structural post-Setup/pre-serialization interval, but caller-side mutation safety and the exact project commit point remain unproven. Do not bind the portable API to a VA or infer that response mutation means delivery commitment.

## Required Honda evidence

1. **Callout interval:** identify the exact caller instructions after successful `AirPlayReceiverSessionSetup` and before serializer consumption, plus every branch/early exit in that interval.
2. **Session liveness:** prove the receiver-session pointer is still valid at the candidate interval and identify its reloadable source.
3. **Request liveness:** prove the parsed Setup request remains valid and can be safely inspected for Type111 there.
4. **Response liveness/ownership:** prove the exact response object, type/mutability, owner, retain/release behavior, and whether the caller can append without corrupting stock Type110 entries.
5. **Allocation ordering:** determine whether listener preparation is safe before, during, or after stock response mutation, and how partial allocation is cleaned.
6. **Mutation ordering:** prove ordering of project response entry construction, attachment, and any rollback if a subsequent step fails.
7. **Serialization outcome:** recover serializer return/error branches, HTTP body/message mutation, and whether a successful serializer return is sufficient for the project transaction's commit signal.
8. **Commit point:** identify the earliest caller-visible point that can safely transition PREPARED → ACTIVE; leave UNKNOWN if no point is proven.
9. **Pre-commit cleanup:** trace every return/error/early-exit path between preparation and commit and show how project resources are rolled back without Honda teardown.
10. **Concurrency and ABI:** determine reentrancy/observer constraints and the caller ABI/register/stack preservation needed for any future implementation; do not design a trampoline or hook in 43L.

## Portable interface to preserve

The future caller can use the conceptual sequence:

```text
prepare_after_stock_setup(session_key, config)
    -> project resources owned by PREPARED transaction
mutate candidate response while preserving stock response on failure
signal response-ready
commit_after_response_commit() only at the commit point proven by 43L
otherwise rollback_before_response_commit()
```

The names above are logical API boundaries, not Honda symbols. If 43L cannot prove an exact commit point, keep the child prepared until a later safe signal or keep the project path disabled; do not guess.
