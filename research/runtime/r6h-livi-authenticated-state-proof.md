# R6H LIVI authenticated-state proof

Pinned LIVI source now marks the proof in `CpStack._handle` only after `handleAuthSetup()` returns a non-null MFi response, the response write callback completes (`mfiAuthSetupResponseWritten`), `PairVerify.controlKeys` is present, and a subsequent RTSP request is parsed in that same `CpSession`. It then calls `ControlSessionDelegate.onAuthenticated(randomUUID())`. Pair verify checks the controller signature against paired state in `PairVerify.m4`; MFi signing remains in `handleAuthSetup`/`MfiSigner`. The random LIVI session UUID is only a correlation identifier, not a phone identifier.

The event is sent over the private same-UID Unix socket. ClarityLink accepts no bare connection: it requires exact protocol version, UUID and proof string, peer UID, limits and generation acknowledgement before returning an authenticated `AuthenticatedSessionHandoff`. No MFi key/certificate private data, challenge, pairing key or control encryption state crosses this interface. Errors are generic and teardown closes the generation.

This is server-side evidence that LIVI executed its MFi signer response path, completed pair verification, and observed a later control request. It does not establish that a real iPhone accepted the exchange; CPC200 is absent and no iPhone session was attempted. Real acceptance requires the Gate 1 ladder evidence.
