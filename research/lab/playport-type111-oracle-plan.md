# PlayPort Mac/iPhone Type111 oracle plan — offline design

**Status: DESIGN_READY, not executed.** This plan targets only the pinned PlayPort `9a0882dd0ffe48e467b59d58b12d81391df55ade`, with xcertplay `17c92439413638dfd1d7f91d7e1c2e7358398762` as a source-level protocol reference. It does not require Honda access, credentials in Git, or changes to ClarityLink's production artifacts.

## Minimal lab change

Create a separate user-controlled PlayPort checkout and a small opt-in cluster profile. Keep default startup unchanged. The profile should accept synthetic cluster width/height/physical dimensions and a selected initial URL; set `AirPlayConfig.cluster` only when the opt-in is explicit. Extend the web UI to route video config/frame events by `streamType` into independent 110 and 111 decoder/canvas instances. The current binary wire messages already carry stream type, while current UI has one canvas.

## Capture only the protocol fields needed

Add bounded, redacted diagnostics that retain:

- iPhone `/info`: only `altScreenURLs` (do not persist the complete plist or unrelated identity fields).
- SETUP request: proposed feature strings and each stream's `type` plus explicitly approved keys needed for interpretation; do not log auth material or serialize whole dictionaries by default.
- SETUP response: accepted type and listener `dataPort` for each screen stream.
- Media: stream type, codec/config arrival, first-frame timestamp, dimensions, and decode result; keep 110 and 111 counters independent.
- UI/control: command type, UUID class (main/alternate/redacted), URL class, and outcome for `showUI`, `stopUI`, and `forceKeyFrame`.

Do not record accessory private keys, pairing material, session secrets, or complete authentication exchanges. Any later phone run requires separate explicit scope and authorized credentials kept outside the repository.

## Acceptance sequence

1. Unit-test default profile still omits cluster and keeps the current single-screen behavior.
2. Synthetic tests prove stream 110 and 111 remain separately keyed end-to-end through media, wire, and decoder routing.
3. On a separately authorized non-vehicle Mac/iPhone run, opt in to the second display and record the minimum fields above.
4. Confirm actual iPhone request/response/media behavior for that iOS build; label it external physical/device observation, not Honda evidence.
5. Keep the center-screen 110 path active throughout the lab run; stop on any session/authentication failure rather than changing keys or pairing identity.

The current milestone performs none of these phone operations. It only establishes that the pinned protocol supports Type111 plumbing and that the normal web renderer still needs a second canvas path.

## xcertplay reference baseline

Before interpreting a later PlayPort observation, compare its redacted metadata with the pinned [xcertplay implementation](https://github.com/shilapi/xcertplay/tree/17c92439413638dfd1d7f91d7e1c2e7358398762): optional type-111 `/info` descriptor with a distinct UUID, `viewAreas`/`initialViewArea`, conditional SETUP `altScreen`, separate `{type,dataPort}` response, and `(session,type)` stream ownership. Treat this as `EXTERNAL_PRIOR_ART`; DiPlay and PlayPort share source lineage, so source agreement is not independent phone evidence.

The oracle should answer, for the recorded iOS build: `altScreenURLs` presence, requested Type111 stream, second data-port connection, distinct `streamConnectionID`, required `enabledFeatures`, codec/config metadata, and observed security variant. Capture only field names/types and approved non-secret values; never retain keys, pairing secrets, or session secrets. This plan is not authorization to run an iPhone session; any phone use remains separately scoped.
