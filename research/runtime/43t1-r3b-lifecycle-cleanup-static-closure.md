# 43T1-R3B — lifecycle cleanup static closure

**Scope:** bounded offline static review of existing repository evidence. The analysis concerns the preserved, hash-matched `jmcs` artifact only where source reports say so. It does not establish a Setup mediation entry point, runtime integration, or authorization.

## Known Honda cleanup/finalizer path

Static reports trace this chain:

1. `_connectionHandleMessage` builds the Setup response and serializes it synchronously. It later releases the response object before the HTTP send path.
2. `HTTPConnectionSendResponse` enters the connection state machine; terminal write/handler errors close the connection.
3. `_connectionFinalize` calls `AirPlayReceiverSessionTearDown` only when its private context's session pointer is non-null. This edge is conditional.
4. Normal `AirPlayReceiverSessionTearDown` dispatches `tearDownStreams` to `AirPlayReceiverSessionPlatformControl`, which handles recognized stream types 100/101/110 and then performs stock screen/stream/control/timing cleanup.
5. Separately, CF runtime `_Finalize` (`0x284d24`) invokes Honda `_AirPlayHandleSessionFinalized` with `(session, context)` and then `AirPlayReceiverSessionPlatformFinalize` (`0x28cd60`). The Honda handler clears/frees Honda-owned context and screen-session state.

Sources: [43L.1 cleanup reachability](../../step-reports/43l1-callout-safety-cleanup-reachability.md), [43L.2 finalizer audit](../../step-reports/43l2-session-finalizer-extension-audit.md), [Honda project-child reachability](../../research/carplay/honda-project-child-cleanup-reachability.md), [finalizer dataflow](../../research/carplay/honda-session-finalizer-dataflow.md).

## Known session identity evidence

`HONDA_CONFIRMED`: the opaque Honda session pointer and context reach the per-session finalizer callback and platform finalizer. `UNKNOWN`: a stable Honda session generation/identifier or pointer non-reuse guarantee. The global app-facing `MC_DEV_CARPLAY_SESSION_DESTROYED` event receives `(interface,event)` and omits the session pointer. The model's `(opaque identity,generation)` key is `MODEL_ONLY`; it cannot be looked up by Honda's current callback without an independently established project association.

## Known Type110 cleanup behavior

`HONDA_CONFIRMED`: within the observed stock response graph, Type110's entry is retained by the streams array, the array by the response dictionary, and nested release callbacks lead to destruction when the caller releases the response. During recognized `tearDownStreams`, the recovered platform-control path handles Type110 along with 100/101. This proves listed static ownership/call edges for the hash-matched artifact, not runtime fault safety or arbitrary future entries. The project Type111 path must not own, remove, or mutate Type110. Type110 preservation in host tests is `MODEL_ONLY`/`LAB_CONFIRMED` only within those test bounds.

## Known unknown-type behavior

`HONDA_CONFIRMED`: the recovered `tearDownStreams` parser skips unknown stream type 111 rather than dispatching it through the Type110 cleanup branch. No evidence shows that Honda's ordinary finalizer enumerates arbitrary stream dictionaries to find project-added Type111 entries. Do not infer Type111 cleanup from Type110 cleanup.

## Known callback/finalizer ownership

The per-session delegate is a fixed Honda-owned 11-word record, copied wholesale by `AirPlayReceiverSessionSetDelegate`; the finalizer callback installed by Honda is not an observer list. The global `g_carplay_cbs` callback record is a fixed 24-byte single slot copied wholesale by `mc_carplay_iface_set_cbs`. No append-only registration, add/remove subscriber API, callback-chain contract, or project registry lookup appears in the reviewed paths. Both replacement options are explicitly rejected as unsafe. The app event is useful as historical/diagnostic evidence only: it lacks session identity.

## Known release/close paths

- Stock Setup local response/array/entry/number references are released on the static branches enumerated by the R2 CFLite audit. Full behavior for arbitrary values, reentry, partial mutation, and all failures is `UNKNOWN`.
- The response dictionary is released after synchronous serialization, before later HTTP send/connection cleanup; it cannot own resources through those later events.
- Connection close can conditionally reach session teardown through a non-null private context session pointer. The conditional edge does not guarantee every connection or failed send reaches session teardown.
- The Honda finalizer releases Honda-owned state. No project child resource pointer or registry is shown at the Honda finalizer.
- Host generation leases, exact-generation close, duplicate suppression, listener cleanup, and rollback remain `MODEL_ONLY`; they do not prove Honda callback reachability.

## Project-child cleanup possibility

**The existing Honda cleanup path cannot presently be treated as a safe cleanup owner for project-created Type111 children.** It can be described as a prerequisite signal only if an independently evidenced non-destructive, session-addressable project association becomes available. Today the session delegate callback is Honda-owned and replacement-based; the global event replacement loses session identity; `tearDownStreams` skips unknown 111; connection teardown is conditional; and finalizer delivery does not cover all pre-session and delivery-failure cases. A project-only lease/registry might provide independent ownership in a future offline design, but this review does not build that model because no safe integration/identity contract is available and the user restricted it to cases where static closure clearly justifies one.

## Failure coverage

The coverage matrix is in [43T1-R3B cleanup coverage matrix](43t1-r3b-cleanup-coverage-matrix.md). In summary:

- Setup success establishes no later cleanup callback for a project child.
- Malformed/stock Setup failure has Honda-local cleanup on observed paths; it should precede project-child creation under the modeled ordering, but that ordering is not an integrated Honda path.
- Serializer/body failure has local object cleanup evidence, but no Honda-to-project resource cleanup edge.
- Bind, accept, unsupported-security, never-connect, stale/duplicate generation behavior is covered only by `MODEL_ONLY` policy/tests.
- Disconnect and terminal send failure can reach conditional Honda session teardown, but Type111 is skipped and no child is reachable.
- Process crash/restart, power loss, and manual CAR-OFF do not have an evidenced project cleanup callback or independent durable resource owner.

## Static blockers

1. No safe Honda callback/dispatch subscription to attach the project child; replacing the per-session delegate or global callback slot is forbidden and would displace Honda state.
2. The known stream teardown skips unknown Type111.
3. The global event callback does not carry the session pointer or project generation.
4. The opaque session pointer has no proven stable generation or non-reuse guarantee.
5. HTTP connection-to-session teardown is conditional; event coverage is incomplete after body install, send/write failure, failed Setup, and process exit.
6. Project resource identity/ownership is not represented in Honda's finalizer or Type110 cleanup graph.
7. CFLite's observed stock retain/release graph does not prove arbitrary Type111 child field compatibility or rollback under interruption/reentry.
8. A new cleanup model cannot solve the absent safe child registration/association contract and is not justified by this static closure.

## Verdict

**`LIFECYCLE_CLEANUP_NOT_SAFE_FOR_PROJECT_CHILDREN`**

The narrower positive finding is that static Honda cleanup is real for Honda-owned session and recognized stock stream state. It does not establish project-child reachability or complete failure coverage. This conclusion does not create or remove a Setup mediation seam and does not authorize runtime work.

### Required questions answered

| Question | Answer | Evidence boundary |
|---|---|---|
| 1. Is there a Honda finalizer path? | Yes. | `HONDA_CONFIRMED` static CF `_Finalize` → Honda callback → `PlatformFinalize`. |
| 2. Enough session identity for project Type111 resources? | No established project association. Per-session Honda callback has an opaque pointer/context; app-facing event lacks the session; stable generation is unknown. | `HONDA_CONFIRMED` call arguments; association/generation `UNKNOWN`. |
| 3. Does it enumerate child stream/resource types? | The recovered `tearDownStreams` path recognizes 100/101/110; no arbitrary project child enumeration is evidenced. | `HONDA_CONFIRMED` bounded parser path. |
| 4. Does it skip unknown types? | Yes, recovered teardown skips unknown 111. | `HONDA_CONFIRMED`. |
| 5. Release/close Type110 safely? | Static ownership and normal teardown edges for observed stock Type110 are traced; arbitrary fault/concurrency safety is not established. | `HONDA_CONFIRMED` listed static path; runtime `UNKNOWN`. |
| 6. Add Type111 child to cleanup-owned set without callback replacement? | No such set or append-only registration is evidenced. | `UNKNOWN` outside reviewed artifact; reviewed mechanisms are Honda-owned replacement slots. |
| 7. Append-only subscription? | None found in reviewed call/data paths. | `HONDA_CONFIRMED` bounded fixed-record behavior; universal absence `UNKNOWN`. |
| 8. Cleanup on success, disconnect, malformed Setup, serializer failure, listener failure? | Not uniformly. Honda object/local cleanup exists on listed branches; project-child cleanup is absent/unwired; failure coverage varies and remains incomplete. | Honda static edges vs `MODEL_ONLY` project policies, per matrix. |
| 9. Honda-confirmed vs model-only? | Honda facts are the call paths, callback-record ownership, Type110 container/release edges, recognized type dispatch, and conditional connection teardown. Leases, generation registry, listener close, rollback, duplicate/stale cleanup are model-only or host test behavior. | Labels are carried per artifact/matrix. |
| 10. Remaining unknowns? | Complete event coverage, pointer reuse/generation, runtime timing, process/power-loss recovery, callback concurrency/reentry, project child CFLite compatibility, and any unreviewed supported extension API. | `UNKNOWN`. |
