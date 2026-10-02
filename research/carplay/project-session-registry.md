# ClarityLink project-session registry

**Classification: `OFFLINE_PROJECT_IMPLEMENTATION` / `SYNTHETIC_TEST_VALUE`.** This model does not read Honda memory or execute Honda code. Honda routing and finalization semantics remain separately classified `HONDA_CONFIRMED` in [the 43J platform trace](honda-platform-lifecycle-seam.md).

## Identity and ownership

`ProjectSessionKey` pairs an opaque, hashable session token with a monotonically increasing per-identity generation. The token is used only as a dictionary key; it is never dereferenced. A key is accepted for preparation at most once. Reusing the same token creates a newer generation, so delayed cleanup for an old generation cannot look up or stop the newer child.

`ProjectChildState` owns only resources implementing `ResourceHandle.close()`: the offline contract can represent listener, accepted socket, crypto, parser, decoder, and renderer handles. Honda Type110 state, Honda crypto/screen/audio objects, Honda delegate/context/platform pointers, and Honda connections are not stored in the registry. Resource handles transfer to the child during preparation. A pre-commit transaction owns the prepared generation and can roll it back; after commit, the registry owns it.

## State and transaction boundary

The phase sequence is `PREPARING → PREPARED → ACTIVE → STOPPING → STOPPED`. Allocation failure rolls back to STOPPED and removes the entry. `mark_response_ready()` records completion of project response construction/mutation; `commit_after_response_commit()` requires that marker and represents the caller's later successful response-transaction commit. The actual Honda callout and commit point remain `UNKNOWN`; this API intentionally carries no Honda address or guessed integration point. Rollback is available until commit.

Project cleanup atomically detaches the exact key from the registry before invoking resource close callbacks, and no registry/state lock is held during close. Each child claims cleanup once, empties its owned resource list before callbacks, releases in reverse acquisition order, and records project cleanup failures independently. A late resource yielded by a factory after concurrent finalization is immediately closed rather than registered.

## Stock-delegating adapters

For `tearDownStreams`, the adapter deep-copies and inspects the synthetic request before stock runs, passes the exact original command/request objects to stock exactly once, and records an equality observation afterward. Only a well-formed explicit stream list containing 111 triggers child cleanup, after stock returns (or raises). The stock return value is returned unchanged; project cleanup failures are recorded and cannot replace it. Malformed input fails open. Unknown types and Type110-only requests leave the child active. Missing `streams`/absent parameters are classified `UNKNOWN` as project teardown semantics and left for unconditional PlatformFinalize cleanup; the model does not import xcertplay behavior as Honda proof.

PlatformFinalize first detaches/stops the matching generation and then calls stock exactly once, without holding registry locks across project resource callbacks or stock. No entry and already stopped state are valid no-ops. Repeated adapter invocations each call their supplied stock callback once; project resource close remains exactly once.

Project transport EOF/failure calls `project_transport_failed` and removes only that project generation. It does not invoke Honda Type110 teardown or mutate audio/parent session state. suggestUI, showUI, stopUI, modesChanged, and requestUI are recordable control events and never tear down the transport in this model.

## Integration contract for Step 43L

43L must statically prove before connecting these portable APIs to any Honda code:

1. Exact successful Setup callout/integration interval.
2. Session pointer liveness at that interval.
3. Parsed request pointer liveness and Type111 inspectability.
4. Mutable response pointer liveness, type, and ownership.
5. Listener allocation ordering relative to stock Setup and response creation.
6. Response mutation ordering and rollback feasibility while preserving stock Type110 entries.
7. Serializer/response transaction success and failure edges.
8. The earliest safe caller-selected commit point for PREPARED → ACTIVE.
9. Cleanup when an error/early exit occurs before successful response commitment.
10. Any concurrency/reentrancy constraints and the caller ABI needed for a future adapter.

Until those facts are established, this is portable synthetic implementation only. It does not make JMCS integration or live testing ready.
## Step 43L Honda transaction boundary

43L maps the portable response transaction to a Honda structural interval: stock Setup succeeds at `0x28af76`; stock caller metadata work ends at `CFObjectSetProperty` return after `0x28afae`; same response enters synchronous plist/body helper at `0x28afba`; helper success returns at `0x28afbe`. Keep the registry PREPARED until that successful return. It is only a candidate ACTIVE commit because Honda's safe callout and direct child cleanup subscription remain unproven. Project preparation and all entry construction precede append; append is the last local response mutation. Pre-serializer project errors fail open to stock. Serializer errors go through Honda's error path and cannot promise stock response delivery. See [43L report](../../step-reports/43l-post-setup-transaction-seam.md).
## Step 43L.1 cleanup guard boundary

Honda cleanup does not presently provide a project-child lookup edge: the HTTP connection's session pointer is conditional; the session delegate is Honda-owned and whole-table replacement would discard its callbacks; PlatformFinalize runs in the finalizer but no child subscription is proven. Therefore a project-owned guard is required if any child is prepared.

Bounded synthetic guard model (not Honda behavior):

1. **Session-start boundary:** Honda's `_AirPlayHandleSessionCreated` runs during receiver session creation, but project observation of it is not proven. A project may mint a generation only at its first safely observed event; treating successful Setup as that event is a hypothesis until an integration seam exists. Key every transaction/resource by `(opaque session pointer, generation)` and never dereference the pointer for registry lookup.
2. The PREPARED transaction exclusively owns the listener, security bytes, parser/renderer state. It has a short preparation lease; expiration before serializer-success always rolls back.
3. Successful serializer return (`0xc8` plus zero statusOut) is the local activation boundary, not phone receipt. Failure/timeout before it rolls back. Duplicate Setup for an already-prepared/active generation is rejected fail-open unless a fully ordered replacement protocol is defined.
4. A stale callback or timeout must carry generation and may close only the matching generation. A newer generation is never stopped by old cleanup.
5. A project-owned activity lease/inactivity watchdog is needed after activation if no Honda finalizer notification can be safely observed. Its duration and renewal signal are not established; this is a material unresolved policy and can terminate a healthy but quiet connection if guessed.
6. **Teardown boundary:** Honda has request-driven `AirPlayReceiverSessionTearDown` and object `_Finalize`/PlatformFinalize boundaries, but neither is proven to notify the project child. On response mutation failure, leave/restore stock graph only when mutation has not begun; otherwise do not claim selective rollback. On serializer failure, detach and close project resources. On HTTP delivery failure or normal session teardown, cleanup must be driven by a proven project notification or the bounded project watchdog; Honda teardown alone is not enough until linked.
7. Cleanup is idempotent, closes resources in reverse acquisition order, erases project secrets, and retains no Honda-owned response/session references beyond the defined transaction.

Lease callbacks now use a versioned `LeaseTicket(ProjectSessionKey, revision)`. Renewal increments the exact generation revision; a delayed ticket from an earlier lease or retired generation is a no-op. Expiration revalidates and detaches the child atomically under the registry lock, then closes resources outside the lock. This is still offline project behavior and does not establish a Honda timer or renewal signal.

The phase/generation/idempotence portions are already `OFFLINE_PROJECT_IMPLEMENTATION`; the required timeout policy and a real event that renews/stops an active child are not proven. Thus `GENERATION GUARD REQUIRED: YES`, `GENERATION GUARD MODEL: PARTIAL`.
