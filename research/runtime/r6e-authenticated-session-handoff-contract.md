# R6E authenticated session handoff contract

`AuthorizedAuthenticationAuthority.open(generation)` returns a single-use `AuthenticatedSessionHandoff`; `LabAuthenticationProvider` checks explicit authorization, authority identity/type, authenticated state and generation. `ReceiverSession` claims it once and passes it to `LabSessionTransport`. The authority must own real iAP2/MFi/SAP and supply a matching authenticated control channel. Python interface conformance is not independent proof of lawful authorization: provider-specific integration needs a documented API and operational ownership review.

The handoff contains an opaque session identifier, generation, authority identity/type, channel, optional opaque security context, capability booleans, and close operation. It contains no private key or challenge material. It is non-serializable, cannot be claimed twice, and closes channel/context idempotently. Receiver teardown closes transport and provider. Reconnect uses the next receiver generation; old handoffs fail. Replay uses `SYNTHETIC` and cannot satisfy a real-iOS gate.

Provider selection currently fails closed for hardware and licensed-service choices because neither adapter nor authority is available. The provider slots are in `auth_providers/`; no vendor API is embedded in `ReceiverSession`.
