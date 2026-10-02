# Step 43Q-B — offline synthetic Type111 generation and lifecycle twin

**Status: IMPLEMENTED AND LOCALLY VERIFIED.** Hosted CI will run after the scoped commit is pushed. This is an offline simulator ownership model. Honda Type111 independent teardown/restart remains `HONDA_UNKNOWN`.

## Starting point and scope

- Starting HEAD: `cd6a3d41ade300f8e528e449abcac0d2bbf8f1e3` (`main`), clean and synchronized with `origin/main`.
- This milestone composes the 43Q-A `LegacyDualScreenTwin` with the existing `ProjectSessionRegistry`; it does not redo or alter 43Q-A crypto derivation.
- No Honda/ADB/vehicle access, live listener, binary modification, `jmcs` work, APK, configuration change, USB/CAN, or runtime integration was performed.

## Ownership and state model

`DualScreenLifecycleTwin` requires an already active Type110 session and rejects pre-existing Type111 state. It keeps the Type110 screen outside the project child registry, at a stable model-local generation `1`. Type111 uses the existing role-tagged screen object and `ProjectSessionKey` with a private parent token plus explicit `TYPE111_SYNTHETIC` role identity. The registry monotonically numbers each Type111 generation.

Creation prepares one project-owned resource handle around the exact `LegacyScreenSession`. Activation reuses `PREPARED → ACTIVE`; teardown/failure/expiry remove only the exact key and close only the screen instance captured by that resource handle. Supersession allocates a new key; the old registry child closes B1 before the replacement screen is inserted. Thus late B1 teardown/failure cannot resolve to “current B” or destroy B2. Restart after stop produces a higher generation and fresh screen, receiver, parser, and CTR objects. Duplicate IDs against A fail with the 43Q-A structured error; restarting with the still-current B ID is rejected without retiring B.

The registry's existing PREPARING/PREPARED/ACTIVE/STOPPING/STOPPED phases are reused. The Type111 lifecycle facade exposes PREPARED as “created”; it adds no parallel state machine. Exact B-only teardown is distinct from explicit `destroy_parent()`, which first stops the project child and then destroys the parent-owned Type110 screen.

## Lease and delayed-callback model

`ProjectSessionRegistry` now issues a `LeaseTicket` containing the exact `ProjectSessionKey` and a monotonically increasing lease revision. Renewal advances the revision and deadline. `reap_lease(ticket)` atomically validates the revision/deadline and detaches that exact child before closing resources outside the registry lock. A previous ticket is therefore a no-op after renewal or generation replacement. `reap_expired` snapshots versioned tickets and revalidates each before acting, preventing a renewal between enumeration and cleanup from being lost.

Tests use an injected fake clock and explicit callback ordering. No sleeps or wall-clock scheduling are involved. The simulator uses deterministic serialized lifecycle ordering; it adds no new threading model.

## Results and evidence

The new `tests/transport/test_type111_lifecycle_twin.py` adds **14 deterministic test cases** covering simultaneous A/B activity; explicit generation; exact and idempotent B teardown; B1→B2 restart/supersession; fresh state; late teardown/failure/activation/renewal; stale lease after replacement; stale expiry after renewal; current lease expiry; malformed-B failure and restart; duplicate ID; separate parent lifecycle state; and parent-versus-child cleanup. Existing `tests/carplay-session-model/test_project_lifecycle.py` continues to exercise registry transactions, idempotent cleanup, generation supersession, expiry, and race ordering.

Verification: focused lifecycle + registry + 43Q-A crypto/parser/KDF set: **105 passed**; 43Q-A regression module and related KDF/parser tests are included. Configured full offline suite: **329 passed, 4 skipped**; self-locator smoke: **3 passed**; configured simulator JavaScript checks: **all passed**; redaction/security tests are included in the full suite; `git diff --check`: **passed**. Relative Markdown links in changed project records: **passed**. Hosted CI is pending the push.

## ECC review

ECC security-review, coding-quality, Python-testing, and lifecycle ownership guidance were applied manually. The review checked exact-key cleanup (no fallback to current B), lease-revision validation, renewal/reaper ordering, one-time resource close, new-state allocation after restart, A receiver/parser/CTR preservation, parent/child distinction, and secret-safe error paths. The resource handle captures the exact screen object. Stale manager actions return false; retired generation feed/activation is rejected. Existing project registry locks remain responsible for registry/resource races; the new façade models ordering deterministically and does not claim a separate concurrent callback scheduler. No dedicated independent ECC reviewer endpoint is available, so this is manual ECC-guided review rather than an independent audit.

## Evidence classifications and limitations

- Existing Honda Type110 behavior remains `HONDA_CONFIRMED` from prior evidence; it is not newly validated here.
- Lifecycle operations proven by deterministic model tests are `LAB_SYNTHETIC_CONFIRMED` only.
- External legacy secondary-screen lifecycle material remains `EXTERNAL_PRIOR_ART`.
- 43P simultaneous two-stream topology remains `CURRENT_IOS_LAB_CONFIRMED` for its tested PlayPort/iPhone profile. 43P did not exercise Type111-only teardown or restart.
- Honda Type111 crypto, ABI, listener, setup acceptance, independent teardown, and restart remain `HONDA_UNKNOWN`.

The model does not establish Honda callback timing, listener ownership, phone behavior, or an integration boundary. `LeaseTicket` is an offline ownership guard, not a proposed Honda timer ABI or verified activity policy.

## Next step

After all final verification, the next bounded milestone is **43R — offline Honda Type111 SETUP response/listener contract implementation based on the sanitized 43P trace**. Do not begin 43R here.
