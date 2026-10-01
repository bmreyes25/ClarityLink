# Step 43K — offline project-session registry

**Starting commit:** `d04aac7ef3c99e135826397819298cc6cc9edb25` (clean `main`).  
**Classification:** `OFFLINE_PROJECT_IMPLEMENTATION`, `SYNTHETIC_TEST_VALUE`. No Honda code was executed or changed; no vehicle, ADB, phone, real keys, private captures, or live Type111/render path was used.

## Implemented

Replaced the initial stop-flag model with `src/carplay-session-model/project_lifecycle.py`: opaque `ProjectSessionKey(identity, generation)`, explicit phases, one-time generation registration, preparation-resource ownership, response-ready/commit/rollback transaction API, stock-delegating control/finalize adapters, project transport-failure cleanup, UI event recording, and cleanup diagnostics. Registry lookups never dereference session identities. A stale generation cannot find or stop a newer generation.

Resources implement one mockable `ResourceHandle.close()` contract and remain project-owned only. During prepare the transaction is the logical owner; after commit ownership transfers to the registry; cleanup clears ownership and detaches the exact generation before closing in reverse acquisition order. Close callbacks execute outside registry/state locks. Partial preparation, cleanup errors, duplicate stop, finalization without a child, and late resource yields after concurrent finalization are covered.

PlatformControl snapshots/inspects the synthetic request before stock. The same command/request objects go to stock exactly once. Only a well-formed explicit stream array containing Type111 triggers project cleanup after stock returns (also in a stock exception path). Type110-only, unknown types, empty arrays, UI commands, and malformed requests preserve the child. Missing stream-list/full-teardown meaning remains conditional/unknown here; PlatformFinalize is the unconditional safety net per Step 43J. Project cleanup errors are recorded and never replace the stock return. PlatformFinalize detaches/cleans project state before invoking stock once, with no registry lock held across resource callbacks or stock.

The response transaction exposes `prepare_after_stock_setup`, `mark_response_ready`, `commit_after_response_commit`, and `rollback_before_response_commit`. No Honda address or guessed commit point is bound. The actual Honda commit point remains unknown and is the subject of 43L.

## Verification

- Focused registry/lifecycle tests: **25 passed**.
- Related negotiation, transport, synthetic lifecycle failure, simulator, renderer mock, and Honda runtime-safety groups: **116 passed**.
- Canonical `PYTHON="$PWD/.venv/bin/python" ./tools/run_tests.sh`: **266 passed, 4 skipped**; locator smoke and JavaScript checks passed.
- Capture-backed replay remains skipped because private fixtures are unavailable; no capture-backed pass is claimed.
- `git diff --check`: PASS.

Tests include stock call count/arguments/result, Type110 and audio-state isolation, Type111 and combined requests, request equality/fingerprint, malformed/unknown input, stock errors, cleanup failures, preparation allocation failure, rollback/serialization failure, commit guard, finalization of prepared/active/absent state, repeated finalization, EOF/teardown/finalization races, in-progress preparation/finalization race, pointer reuse, UI/transport separation, and 256 short event-sequence combinations. Each mock project resource is released at most once.

## Decision gate

| Gate | Result |
|---|---|
| PROJECT SESSION REGISTRY | READY |
| GENERATION PROTECTION | READY |
| TWO-PHASE CHILD SETUP | READY (portable transaction contract) |
| PLATFORMCONTROL ADAPTER | READY (synthetic only) |
| PLATFORMFINALIZE ADAPTER | READY (synthetic only) |
| TYPE110 PRESERVATION | PASS |
| AUDIO PRESERVATION | PASS |
| STOCK CALL EXACTLY ONCE | PASS |
| STOCK REQUEST IMMUTABILITY | PASS (adapter preserves object/arguments; equality recorded) |
| STOCK RETURN PRESERVATION | PASS |
| PROJECT RESOURCE EXACTLY-ONCE CLEANUP | PASS |
| CONCURRENCY MODEL | PASS (threaded races plus deterministic sequence enumeration) |
| POINTER REUSE PROTECTION | PASS |
| UI/TRANSPORT SEPARATION | PASS |
| PROJECT CHILD LIFECYCLE | OFFLINE_IMPLEMENTATION_READY |
| POST-SETUP STATIC SEAM | READY_TO_AUDIT |
| JMCS INTEGRATION DESIGN | NOT READY |
| JMCS live / Type111 live / ExternalDisplay live | NOT READY |
| LD_PRELOAD | PARKED |

**Biggest blocker:** Honda's exact successful Setup-to-serialization commit/rollback window and a safe integration mechanism remain unproven.  
**Next action:** Step 43L — statically prove the exact post-Setup project-child creation and commit seam in Honda `jmcs`.
