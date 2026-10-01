# PlayPort Mac/iPhone Type111 oracle plan — offline design

**Status: IMPLEMENTED OFFLINE; 43P auth-source policy revised; live session pending validation.** Step 43O built an isolated, opt-in PlayPort lab and redacted diagnostics. Step 43P is one controlled current-iPhone trace. The plan targets the pinned PlayPort `9a0882dd0ffe48e467b59d58b12d81391df55ade`, with xcertplay `17c92439413638dfd1d7f91d7e1c2e7358398762` as a source-level protocol reference. It does not require Honda access, credentials in Git, or changes to ClarityLink's production artifacts.

## Minimal lab change

Create a separate user-controlled PlayPort checkout and a small opt-in cluster profile. Keep default startup unchanged. The profile should accept synthetic cluster width/height/physical dimensions and a selected initial URL; set `AirPlayConfig.cluster` only when the opt-in is explicit. Extend the web UI to route video config/frame events by `streamType` into independent 110 and 111 decoder/canvas instances. The current binary wire messages already carry stream type, while current UI has one canvas.

## Capture only the protocol fields needed

Add bounded, redacted diagnostics that retain:

- iPhone `/info`: only `altScreenURLs` (do not persist the complete plist or unrelated identity fields).
- SETUP request: proposed feature strings and each stream's `type` plus explicitly approved keys needed for interpretation; do not log auth material or serialize whole dictionaries by default.
- SETUP response: accepted type and listener `dataPort` for each screen stream.
- Media: stream type, codec/config arrival, first-frame timestamp, dimensions, and decode result; keep 110 and 111 counters independent.
- UI/control: command type, UUID class (main/alternate/redacted), URL class, and outcome for `showUI`, `stopUI`, and `forceKeyFrame`.

Do not record accessory private keys, pairing material, session secrets, or complete authentication exchanges. The 43P phone run is explicitly scoped by the current user request. Its authentication source may be a trusted identity/service or the PlayPort-documented shared experimental identity, classified `EXPERIMENTAL_LAB_ONLY`; see the gate below.

## 43P authentication source and handling gate

PlayPort requires an accessory authentication backend; a physical MFi chip is not required. Bluetooth is the iAP2 bootstrap transport and Wi-Fi carries the later CarPlay session. Xcode and iPhone Developer Mode are not accessory credentials.

For this isolated personal lab run only, the user explicitly permits PlayPort's documented DiPlay experimental identity as `EXPERIMENTAL_LAB_ONLY`. The current official DiPlay release is v0.2.6. Its release and notices describe an experimental identity recovered from public Carlinkit firmware, intentionally present in the release APK, extractable and shared, not newly provisioned for DiPlay, not Apple-certified, and not guaranteed to remain accepted. PlayPort's README still points at an older release; use current official DiPlay release metadata and verify its published APK checksum before extraction. This authorization is limited to one non-Honda Mac/iPhone observation.

Handling requirements:

- Store only the two required identity files under an owner-only directory outside both Git repositories; use directory mode `0700` and file mode `0600`.
- Do not put the APK, private key, certificate, or copies in either repository, source control, logs, terminal output, or capture artifacts. Extract only the identity files from the checksum-verified official release APK.
- Classify the identity `EXPERIMENTAL_LAB_ONLY`, never `TRUSTED`, production, or Honda evidence. The local key/certificate match test proves pair consistency only; it does not prove iPhone acceptance or Apple certification.
- Run PlayPort's `MfiIdentityTest` from the external files without displaying them. Verify redaction behavior and all Step 43O suites again before phone pairing.
- Oracle output remains allowlist-only: no certificate, private key, challenge, signature, bearer token, pair-verify material, session/media keys, IVs/nonces, raw packets, or media payloads.
- Do not reuse this shared identity for ClarityLink, Honda, deployment, distribution, or any production design. No Honda device, Honda ADB, Honda firmware, jmcs, trampoline, CAN, or block device is in scope.

### 43P acceptance criteria

- **AC-43P-AUTH-1 (required):** the APK matches the official release SHA-256; only the expected identity assets are extracted outside both repositories; permissions are `0700`/`0600`; no credential is tracked. Verify with release metadata, archive member names, hash, file metadata, and Git status only.
- **AC-43P-AUTH-2 (required):** `MfiIdentityTest` passes with the external files and emits no key/certificate bytes. This proves parse and key/certificate match, not iPhone trust. Verify the test result and review its output.
- **AC-43P-AUTH-3 (required):** focused redaction tests and full ClarityLink, PlayPort Gradle, and web suites pass after provisioning; diagnostic output contains only allowlisted metadata. Verify by tests and log-path review.
- **AC-43P-LIVE-1 (required):** before starting PlayPort, confirm no Honda ADB target, correct lab/ClarityLink commits, intended network binding, separate 110/111 canvases, and diagnostics opt-in. Only then pair the user's physical iPhone and run one baseline session. Verify the receiver is bound to the intended lab host and only redacted artifacts are created.
- **AC-43P-LIVE-2 (required):** label the auth source `EXPERIMENTAL_LAB_ONLY` and protocol observations `CURRENT_IOS_LAB_CONFIRMED`; make no Honda or production claim. Verify the final report and sanitized JSON artifacts.

## Acceptance sequence

1. Unit-test default profile still omits cluster and keeps the current single-screen behavior.
2. Synthetic tests prove stream 110 and 111 remain separately keyed end-to-end through media, wire, and decoder routing.
3. On the explicitly scoped non-vehicle Mac/iPhone run, use the validated `EXPERIMENTAL_LAB_ONLY` identity, opt in to the second display, and record the minimum fields above.
4. Confirm actual iPhone request/response/media behavior for that iOS build; label it external physical/device observation, not Honda evidence.
5. Keep the center-screen 110 path active throughout the lab run; stop on any session/authentication failure rather than changing keys or pairing identity.

Step 43O performed none of these phone operations. The pinned protocol supports Type111 plumbing; the local lab now has a separate browser canvas/decoder and redacted observation events. Implementation details and verification are in [the lab implementation report](playport-type111-oracle-implementation.md).

## xcertplay reference baseline

Before interpreting a later PlayPort observation, compare its redacted metadata with the pinned [xcertplay implementation](https://github.com/shilapi/xcertplay/tree/17c92439413638dfd1d7f91d7e1c2e7358398762): optional type-111 `/info` descriptor with a distinct UUID, `viewAreas`/`initialViewArea`, conditional SETUP `altScreen`, separate `{type,dataPort}` response, and `(session,type)` stream ownership. Treat this as `EXTERNAL_PRIOR_ART`; DiPlay and PlayPort share source lineage, so source agreement is not independent phone evidence.

The oracle should answer, for the recorded iOS build: `altScreenURLs` presence, requested Type111 stream, second data-port connection, distinct `streamConnectionID`, required `enabledFeatures`, codec/config metadata, and observed security variant. Capture only field names/types and approved non-secret values; never retain keys, pairing secrets, or session secrets. This plan authorizes only the bounded 43P session described above; it does not authorize Honda access or broader phone/authentication experiments.

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
