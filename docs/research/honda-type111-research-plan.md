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

Step 43D completed a deeper stock SETUP trace: `type` selects stream branch; Type-110 `streamConnectionID` feeds the screen KDF; `dataPort` is sourced from the listener; no direct `/info` UUID join was recovered. See [Honda Setup identity](../../research/carplay/honda-setup-stream-identity.md) and [source-pinned identity prior art](../../research/carplay/setup-stream-identity-prior-art.md). **Next bounded gate:** statically assess the successful stock Setup return / pre-serialization boundary, response ownership, mutability, and failure rollback for an optional project-owned entry. This is design analysis only, not a hook implementation or live-ready decision.

### 2. Honda UI-control command audit

Search static code and preserved observations for `suggestUI`, `showUI`, `stopUI`, `SecondDisplayMode`, `ViewArea`, `ViewAreaChanged`, and `forceKeyFrame`, then follow candidate strings/constants through parser, dispatch, and serialization paths. Record `ABSENT_LITERAL` only for the searched artifact and method. MHI2 sender lifecycle is prior art; it does not establish the Honda command set.

### 3. Type110 to possible Type111 crypto reuse audit

Trace allocation and ownership for receiver-session master material, `streamConnectionID`, AES key/IV derivation, and CTR state. Determine whether a second identifier can be derived without mutating/resetting the Type110 state. Do not infer Type111 KDF compatibility from the confirmed Type110 KDF or from MHI2. Use synthetic keys in tests; never check in live keys or capture payloads.

### 4. Safe stock-first jmcs integration seam analysis

Revisit the process entry and load path only with a concrete candidate and explicit rollback/failure model. The prior `LD_PRELOAD` candidate remains parked/unknown; service `setenv` capability does not prove that the archived Honda linker honors it. Any eventual integration must call stock behavior first, preserve its Type110 response and state, fail closed on binary mismatch, and have an independently reviewed recovery path. No live seam is currently ready.

### 5. ExternalDisplay synthetic renderer proof

Continue with host-side mocks and synthetic frames to define the narrow renderer input/output boundary. Then determine whether an in-process adapter can be tested against a reproduced host interface without asserting a public Binder/API that the Honda audit did not find. Preserve the present finding: a render host exists, but a supported companion frame/Surface API has not been found.

### 6. Observation-only stock iPhone/Honda logging baseline

Only after review and explicit milestone scope, define a minimal observation-only baseline that changes no negotiation, starts no additional listener, and captures no secrets or personal data. Compare the baseline to static hypotheses; keep Type110 normal. This gate is not currently authorized as a live test by this plan.

### 7. Minimal live negotiation test design

Only after the previous gates have adequate evidence, specify a reversible test whose first success criterion is normal center Type110 plus observed iPhone Type111 request/second endpoint. Rendered video is not needed for the first negotiation proof. Require stop conditions, rollback, logging limits, and a ready integration seam. Current status: NOT READY.

## Research record format

For each field or behavior record: claim; evidence class; exact Honda artifact/location; external URL and pinned revision if relevant; what the evidence proves; what it does not prove; remaining question; next bounded action. Keep all prior reports and evidence intact. Update [EVIDENCE_INDEX.md](../../EVIDENCE_INDEX.md) when a claim's evidence changes, [PROJECT_STATE.md](../../PROJECT_STATE.md) when a milestone materially changes knowledge, and [NEXT_ACTION.md](../../NEXT_ACTION.md) with one concrete technical task.
