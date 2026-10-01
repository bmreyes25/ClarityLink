# PlayPort Mac/iPhone Type111 oracle plan — offline design

**Status: IMPLEMENTED OFFLINE; no phone session performed.** Step 43O built an isolated, opt-in PlayPort lab and redacted diagnostics. A current-iPhone trace remains a separate Step 43P scope. The plan targets only the pinned PlayPort `9a0882dd0ffe48e467b59d58b12d81391df55ade`, with xcertplay `17c92439413638dfd1d7f91d7e1c2e7358398762` as a source-level protocol reference. It does not require Honda access, credentials in Git, or changes to ClarityLink's production artifacts.

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

Step 43O performed none of these phone operations. The pinned protocol supports Type111 plumbing; the local lab now has a separate browser canvas/decoder and redacted observation events. Implementation details and verification are in [the lab implementation report](playport-type111-oracle-implementation.md).

## xcertplay reference baseline

Before interpreting a later PlayPort observation, compare its redacted metadata with the pinned [xcertplay implementation](https://github.com/shilapi/xcertplay/tree/17c92439413638dfd1d7f91d7e1c2e7358398762): optional type-111 `/info` descriptor with a distinct UUID, `viewAreas`/`initialViewArea`, conditional SETUP `altScreen`, separate `{type,dataPort}` response, and `(session,type)` stream ownership. Treat this as `EXTERNAL_PRIOR_ART`; DiPlay and PlayPort share source lineage, so source agreement is not independent phone evidence.

The oracle should answer, for the recorded iOS build: `altScreenURLs` presence, requested Type111 stream, second data-port connection, distinct `streamConnectionID`, required `enabledFeatures`, codec/config metadata, and observed security variant. Capture only field names/types and approved non-secret values; never retain keys, pairing secrets, or session secrets. This plan is not authorization to run an iPhone session; any phone use remains separately scoped.

## Step 43O build requirements: current-phone observation readiness

Use the confirmed xcertplay, DiPlay, PlayPort, MHI2, and CPC200 material as reference profiles only. Do not add a protocol command whose purpose is to explicitly “create Type111.” The external working hypothesis is that a coherent secondary-display advertisement/feature negotiation may cause the phone to request a Type111 stream; only Step 43P observation can confirm or refute that for a specified iOS build.

The lab prepares redacted diagnostics for the following, without emitting raw authentication plists or secrets. It cannot yet establish the phone's answers:

### Phone requests and negotiation

- `/info` `altScreenURLs` presence and URL values (bounded allowlist; no other identity fields).
- advertised display URL list and display UUID correlation class (main/secondary/unmatched; do not log full device identifiers).
- top-level SETUP feature proposal and receiver enabled-feature result/intersection.
- exact Type110-versus-Type111 SETUP ordering.
- Type111 descriptor key names, `streamConnectionID` presence (not its raw value), and response `{type,dataPort}`.
- whether a second TCP/data-port connection opens and whether it maps to the Type111 request.

### Receiver-generation and media facts

- receiver `sourceVersion` and advertised feature category.
- per-stream security category only (`legacy AES`, `modern AEAD`, `clear/unknown`); never log keys, IVs, nonces, or decrypted payloads.
- VideoConfig framing/codec family and VideoFrame envelope category, without saving media payloads.
- timestamps/counters sufficient to associate config/frame start/stop with Type110 or Type111.

### Independent Type111 lifetime

Model and instrument separate events:

```text
TYPE111_SETUP
TYPE111_SOCKET_OPEN
TYPE111_VIDEO_START
TYPE111_VIDEO_STOP
TYPE111_TEARDOWN
```

Keep Type110 active and observable across a Type111 stop/restart scenario. Step 43O should include synthetic fixtures/tests proving the diagnostic/event model can represent `Type110 ACTIVE` throughout repeated Type111 start/stop cycles. Step 43P can determine whether the selected phone and PlayPort profile actually exhibit that sequence. Compare cautiously with the pinned CPC200 logs and MHI2 lifecycle notes; those sources describe their own adapters/builds and are not evidence of Honda behavior or a universal lifecycle guarantee.

Do not elevate CPC200's logged Type111-before-Type110 setup example into an ordering requirement. Record the actual iPhone order. Treat any claimed independent Type111 stop/start behavior as external to the source/build that demonstrated it; the current CPC200 source note establishes a logged setup ordering, not a universal lifetime contract.

## Future Step 43Q — conditional, not part of 43O

After the oracle is built and a separately scoped 43P trace is reviewed, consider **Step 43Q: offline Honda legacy Type111 crypto/lifecycle twin**. Use only Honda-confirmed Type110 crypto behavior plus explicitly external Type111 evidence and synthetic inputs. Prove distinct IDs yield independent keys/IVs and CTR state; B reset/teardown/malformed frames cannot alter A; duplicate IDs are handled explicitly; generation replacement closes only the project-owned B state. Do not access live keys, implement runtime attachment, or execute Honda code. Do not start 43Q before 43P has supplied the protocol observations it is meant to model.
