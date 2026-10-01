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
