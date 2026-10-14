# CL-IMP-06 — Type111 setup and stock-session delegation

**Status:** offline mock integration implemented. Honda production integration remains disabled. No Honda, vehicle, stock process, or live-iPhone operation was performed.

## Delegation boundary

`claritylink_jmcs.stock_delegation` composes the existing `Type111SetupContract` with an explicit `MockStockPrimarySession`. The mock represents the primary owner and accepts only an explicitly opened local generation. It returns a fixture-supplied primary response; it does not communicate with Honda or implement Apple's/Honda's serializer.

The coordinator calls the mock primary setup first, captures its response, then invokes the existing Type111 listener and serialization transaction. It returns the original primary snapshot whenever the secondary request is rejected, listener preparation fails, serialization fails, or the session generation is revoked during setup. The Type110 owner remains separate from the Type111 child.

Secondary teardown closes only the active Type111 lifecycle child and leaves the mock primary owner active. Session revocation rejects stale setup and closes the secondary child before revoking the mock primary session. Setup calls are serialized under a reentrant lock, while reentrant setup attempts are rejected.

## Validation coverage

The new integration tests cover Type111-first ordering, stock-first call order, primary response preservation, malformed and duplicate IDs, listener failure, serializer failure, secondary-only teardown, stale generation rejection, and session revocation during the serializer callback. Existing Type111 contract tests continue to cover listener ownership, response rollback, duplicate stream parsing, child generations, and cleanup.

These are host tests of a mock interface. They do not prove a Honda delegation hook, a stock session handoff, actual Honda Type111 admission, or genuine iPhone authentication. Unknown production cryptography remains fail closed and no guessed protocol fields were added.
