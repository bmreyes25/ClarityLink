# Honda Type111 research plan

This plan converts external CarPlay/AltScreen prior art into bounded Honda-specific questions. It does not treat Apple, xcertplay, MHI2, or CPC200 behavior as Honda evidence. Current baseline: [project state](../../PROJECT_STATE.md), [evidence index](../../EVIDENCE_INDEX.md), and [prior-art audit](carplay-altscreen-prior-art.md).

## Current evidence boundary

- `HONDA_CONFIRMED`: the stock `/info` builder returns an array-shaped `displays` value but adds one descriptor; recovered fields include `uuid`, `features`, `maxFPS`, and pixel/physical dimensions. The stock Setup path handles Type110 and skips unsupported Type111 without producing a Type111 response. Type110 screen crypto uses receiver-session master material and a `streamConnectionID`. See linked Honda notes in the evidence index.
- `EXTERNAL_PRIOR_ART`: Apple documents multiple independent H.264 vehicle-display streams; xcertplay emits distinct main/alternate descriptors; MHI2 reports a working stock-first Type111 path; CPC200 materials describe their own navigation-video/focus flow.
- `SYNTHETIC_TEST_VALUE`: offline Strict Honda and Hypothetical Type111 modes, generated ScreenStream envelopes, generated H.264, and mock Display 1 frames exercise model behavior only.
- `HYPOTHESIS`: keep Type110 untouched and add only Type111-owned state; model transport, UI context, and view-area geometry separately.
- `UNKNOWN`: Honda Type111 schema/security/trigger, display-to-stream identity, safe jmcs entry seam, and real ExternalDisplay frame handoff.

## Ordered research gates

### 1. Honda `/info` differential audit — completed, literal scope

Step 43A compared the exact phone-facing Honda descriptor construction path with xcertplay pinned at `de9647f4bdfb1be356bed4cac0519400473712a6`. The field-by-field status, artifact addresses, confidence, and limitations are in [Honda `/info` Type111 differential](../../research/carplay/honda-info-type111-differential.md). Honda's `/info` path and one `ScreenCopyMain()` descriptor are confirmed; the listed display keys are classified per descriptor-builder/literal evidence. The audit does not establish which fields are mandatory for Honda or Apple, and no `ABSENT_LITERAL` result means semantic absence.

**Follow-up static task:** trace `ScreenCopyMain()` property sources and the `AirPlayReceiverSessionScreen_CopyDisplaysInfo` (`0x287ae0`) CFDictionary insertions, then inspect xrefs for `forceKeyFrame`/`forceKeyFrameNeeded` and `AirPlayReceiverSessionForceKeyFrame`. Determine whether a parallel descriptor source, implicit role property, or relevant UI/control equivalent exists. Do not implement a second descriptor or Type111 handler.

Step 43D completed a deeper stock SETUP trace: `type` selects stream branch; Type-110 `streamConnectionID` feeds the screen KDF; `dataPort` is sourced from the listener; no direct `/info` UUID join was recovered. See [Honda Setup identity](../../research/carplay/honda-setup-stream-identity.md) and [source-pinned identity prior art](../../research/carplay/setup-stream-identity-prior-art.md). Step 43M selected the existing serializer callsite `0x28afba` as the narrowest future stock-delegating seam. Step 43N implemented and tested only an offline Thumb control-flow/ABI model and strict target fingerprints. See the [43N report](../../step-reports/43n-trampoline-and-type111-oracle.md) and [target plan](../../research/carplay/honda-minimal-future-trampoline-target.md). No runtime attachment is implemented.

Pinned DiPlay and PlayPort work supplies stronger **EXTERNAL_PRIOR_ART** for Type111 and an out-of-car iPhone oracle. DiPlay's pinned docs report physical iOS 27 cluster-map testing (**EXTERNAL_PHYSICAL_VALIDATION**); that does not prove Honda fields or crypto. Step 43O built a separate pinned PlayPort checkout with an opt-in synthetic cluster profile, independent 110/111 browser decoders, Type111-only teardown isolation, and redacted JSON diagnostics. See the [DiPlay differential](../../research/carplay/diplay-type111-differential.md), [PlayPort differential](../../research/carplay/playport-type111-differential.md), [security differential](../../research/carplay/honda-vs-modern-type111-security.md), [oracle plan](../../research/lab/playport-type111-oracle-plan.md), and [implementation report](../../research/lab/playport-type111-oracle-implementation.md). Step 43O used no phone. Step 43P is the next separately scoped Mac/iPhone observation; it is not Honda testing.

### 2. Honda UI-control command audit

Search static code and preserved observations for `suggestUI`, `showUI`, `stopUI`, `SecondDisplayMode`, `ViewArea`, `ViewAreaChanged`, and `forceKeyFrame`, then follow candidate strings/constants through parser, dispatch, and serialization paths. Record `ABSENT_LITERAL` only for the searched artifact and method. MHI2 sender lifecycle is prior art; it does not establish the Honda command set.

### 3. Type110 to possible Type111 crypto reuse audit

Cross-platform legacy evidence now narrows this from an unknown crypto design to a strong hypothesis: pinned MHI2 uses its stock legacy per-screen AES KDF with its Type111 `streamConnectionID`, and pinned WirelessCarPlay's legacy screen path passes its own stream ID and session AES material to the same named derivation family. See [legacy AES Type111 cross-reference](../../research/carplay/legacy-aes-type111-cross-reference.md). This does **not** establish Honda Type111: Honda ABI, ownership, second CTR context, and isolation still require offline modeling against Honda-confirmed Type110 primitives. Use synthetic values only; never include live keys or capture payloads.

### 4. Minimal stock-delegating callsite trampoline model (offline) — completed in 43N

Step 43N added an offline-only model and target compatibility planner. No loader, installer, patch bytes, or Honda runtime behavior is proven. `LD_PRELOAD` remains parked.

### 5. PlayPort Mac/iPhone Type111 oracle (43O offline build complete; phone observation in 43P)

Step 43O implemented an isolated opt-in cluster profile, separate 110/111 frontend render paths, Type111 teardown isolation, and allowlisted diagnostics for feature/order, endpoint, media category, and independent lifecycle. Full Gradle and web builds pass. The current PlayPort screen parser is ChaCha-based; its diagnostic value describes the local parser path only. Step 43O made no phone connection. Step 43P is the next separately scoped trace for a selected iOS build. Do not vendor upstream code. See the [oracle implementation](../../research/lab/playport-type111-oracle-implementation.md) and [redaction contract](../../research/lab/playport-redaction-contract.md).

For this one non-Honda 43P lab observation, the user explicitly permits PlayPort's documented shared DiPlay experimental identity, classified `EXPERIMENTAL_LAB_ONLY`. This is not a private/unique production identity, not Apple certification, and not Honda evidence. Use only a checksum-verified current official release; keep the identity outside both repositories with owner-only permissions; never log, commit, redistribute, or include it in capture artifacts. Validate the certificate/key pair using PlayPort's test before Bluetooth pairing. Physical MFi chip, Xcode, and iPhone Developer Mode are not required for the receiver authentication exchange. This exception does not change any later ClarityLink or Honda credential requirements.

### 5a. Conditional Step 43Q: offline legacy Type111 crypto/lifecycle twin

Only after 43O is built and 43P observations are reviewed, model a second legacy AES screen context using Honda-confirmed Type110 primitives and synthetic second IDs. Prove independent keys/IVs/CTR state and that Type111 stop, restart, or malformed frames cannot affect Type110. This is not runtime attachment or Honda Type111 confirmation.

### 6. ExternalDisplay synthetic renderer proof

Continue with host-side mocks and synthetic frames to define the narrow renderer input/output boundary. Then determine whether an in-process adapter can be tested against a reproduced host interface without asserting a public Binder/API that the Honda audit did not find. Preserve the present finding: a render host exists, but a supported companion frame/Surface API has not been found.

### 7. Observation-only stock iPhone/Honda logging baseline

Only after review and explicit milestone scope, define a minimal observation-only baseline that changes no negotiation, starts no additional listener, and captures no secrets or personal data. Compare the baseline to static hypotheses; keep Type110 normal. This gate is not currently authorized as a live test by this plan.

### 8. Minimal live negotiation test design

Only after the previous gates have adequate evidence, specify a reversible test whose first success criterion is normal center Type110 plus observed iPhone Type111 request/second endpoint. Rendered video is not needed for the first negotiation proof. Require stop conditions, rollback, logging limits, and a ready integration seam. Current status: NOT READY.

## Research record format

For each field or behavior record: claim; evidence class; exact Honda artifact/location; external URL and pinned revision if relevant; what the evidence proves; what it does not prove; remaining question; next bounded action. Keep all prior reports and evidence intact. Update [EVIDENCE_INDEX.md](../../EVIDENCE_INDEX.md) when a claim's evidence changes, [PROJECT_STATE.md](../../PROJECT_STATE.md) when a milestone materially changes knowledge, and [NEXT_ACTION.md](../../NEXT_ACTION.md) with one concrete technical task.
# Step 43N external protocol reference update

xcertplay is pinned at `17c92439413638dfd1d7f91d7e1c2e7358398762` as `EXTERNAL_PRIOR_ART`. See [its Type111 differential](../../research/carplay/xcertplay-type111-differential.md) and the [Honda/xcertplay/DiPlay/PlayPort matrix](../../research/carplay/honda-xcertplay-diplay-playport-differential.md). Use it to reduce generic schema archaeology, while keeping the remaining questions Honda-specific: second-stream security derivation, minimum features for the current iPhone, independent listener coexistence with Honda Type110, and renderer attachment. External code agreement is not Honda proof; do not copy xcertplay crypto or GPL implementation source. The existing selected Honda attachment callsite remains `0x28afba`.
