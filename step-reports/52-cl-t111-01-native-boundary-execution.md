# CL-T111-01 — native boundary execution checkpoint

**Date:** 2026-11-11
**Result:** Honda-native constructor and Type111 candidate helper executed; stock-delegating callsite not reached.
**Disposition:** CL-T111-01 acceptance remains incomplete. `HONDA_TYPE111_NOT_PROVEN` and `VEHICLE_DEPLOYMENT_NOT_AUTHORIZED` remain in force.

## Scope and exact source revisions

This bounded offline task used a clean worktree based on `origin/main` at `f32f87d3f5737f3fda8d50e06ab9663c4087a810`. The original `cl-r4-reliability-completion` worktree and private research were preserved. `safeForHonda() == false` remains unchanged. No vehicle, live ADB, connected phone, receiver installation, firmware modification, or deployment operation was performed.

- PR #117 pass-through machinery was inspected and tested at `cfd64183b02840ff75646d93babbac6e17eb3f71`.
- PR #153 native `/info` helper was inspected and tested at `a945ead50a4cd36db935b7865a15bb88f6a1f56f`.
- The helper C and header source hashes at that PR head are `3a6274ccee50cf70a2fdde0d653791a1c4deb6125335e2bf51731acb44cd03f5` and `bd363e1184fd1c14fee75f975f3182b56ba743409a71f49e27c15fd2a5f326d6`. They match the source copies used in the preserved CL-61 native harness.

PR #117's patcher creates an offline pass-through-only copy. Its Thumb callsite redirects to a Thumb tail branch to Honda's original callee; this preserves the call's incoming arguments and return continuation by construction, but the actual patched callsite has not been reached in the archived runtime. PR #153 supplies candidate construction code; it is not connected to Honda's `/info` callback and does not start or advertise a Type111 listener.

## Native execution

The archived ARMv7/API17 test image was booted offline in QEMU with networking disabled. Stock and modified receiver images were exercised in separate boots. The current PR #117 appended-segment patcher was also run against a private extracted copy of the exact pinned original ELF. The generated output matched the archived modified image used by the runtime probe. Private binaries, manifests, addresses, and raw logs remain outside Git.

The test directly invoked genuine Honda native `ScreenCopyMain` and `AirPlayReceiverSessionScreen_CopyDisplaysInfo` functions from each image. The returned objects were genuine Honda CFLite objects. The default primary descriptor was a dictionary with seven entries; its UUID value had CFString type. The same descriptor shape, field types, and values were observed in stock and modified runs. This establishes bounded constructor equivalence for that default profile only.

The test then called the PR #153 helper directly, using the genuine Honda Screen/descriptor, the verified Honda retain/release callbacks, and Honda CFLite operations. In each image, three iterations produced an augmented array containing the exact primary descriptor pointer followed by a distinct candidate descriptor; the original input remained at one entry. A controlled allocation failure, invalid candidate UUID, and incomplete adapter each returned an error, null output, and unchanged input. Candidate fields and UUID were test inputs, not Honda-provided Type111 values.

This is `HONDA_CF_INTEGRATION_TESTED` and `TYPE111_INFO_CANDIDATE_TESTED`, bounded to the constructor/helper path. It does not establish iPhone acceptance, production display metadata, or Type111 advertisement readiness.

## Wrapper, session, and ownership limits

The original `/info` stock callee and either patched callsite were **not executed**. The pass-through tests execute a synthetic downstream callee; they verify the model's exactly-once call, register/stack, error, and Type110 isolation contracts, not the Honda function.

The real displays callback requires a Honda-created receiver session and its associated Screen. The preserved receiver startup reaches an archived Bionic deliberate-fault path before either patched callsite or the receiver's session-creation path. CL-62 through CL-65 did not establish a genuine session: the callback was not attempted with fabricated state, and the process-attribution attempts did not produce a verified session context. This session/Screen requirement is confirmed for callback augmentation; available evidence does not establish that the original `/info` callee itself requires a receiver session. No receiver session, callback dispatch, response serialization, listener, Type111 security context, or phone negotiation was invented or tested here.

The helper's input immutability and short-run retain/release behavior were exercised through genuine Honda CFLite. Host CoreFoundation serialization and API17 ARM synthetic-callback tests passed separately. The Honda receiver serializer was not reached, so Honda serialization equivalence, long-duration leak behavior, session teardown, and full Type110 runtime preservation remain unverified. No Type111 receiver was advertised.

## Focused verification

All results below are tied to the exact public source revisions above:

| Verification | Result | Evidence boundary |
|---|---:|---|
| PR #117 rewriter, Thumb setup shim, and existing-call wrapper contract suites | 47 passed; 3 subtests passed | Synthetic caller/callee and memory fixtures; not Honda callee execution |
| PR #153 host CoreFoundation, API17 ARMv7 Thumb build, and ARM execution suites (`CL_NATIVE_REQUIRE_TARGET=1`, NDK r23c) | 3 passed | Host CoreFoundation and synthetic ARM callbacks; not Honda CF |
| Archived Honda constructor/helper probe, stock image | 3/3 helper iterations passed; all three injected negative cases returned safely | Genuine Honda constructor and CFLite functions/objects; helper called directly by harness |
| Archived Honda constructor/helper probe, modified image | 3/3 helper iterations passed; all three injected negative cases returned safely | Same bounded path; output matched stock for tested constructor fields and primary identity |
| Exact PR #117 patcher output compared with archived modified image | Match | Private offline ELF identity/layout check; no private target details published |

The CL-61 runtime output confirms the expected markers and clean exits for both images. The host serialization test validates the helper's generic host-CF path only; it is not evidence that Honda's receiver serializer accepts the candidate.

## Acceptance status and next dependency

| CL-T111-01 condition | Status |
|---|---|
| Hash-verified original and isolated modification | Verified in the private archived runtime and exact PR #117 patcher comparison; private target identity retained outside this report |
| ARMv7/Thumb pass-through mechanics | Synthetic suite passed; actual patched callsite not reached |
| Genuine original Honda callee invoked exactly once | Not established |
| Genuine Honda CFLite constructor/helper boundary | Executed and bounded stock/modified comparison passed |
| Honda callback, serializer, and Type110 runtime equivalence | Not established |
| CL-T111-01 exit criteria | **Not met** |

The immediate blocker is that the archived receiver startup stops before either patched callsite. A future bounded attempt needs a legitimate, process-attributed offline startup path that reaches the selected stock call with genuine arguments; the `/info` callee's session dependency remains unestablished. Independently, callback augmentation cannot proceed until Honda itself creates a genuine receiver session and Screen association. Further startup attempts require a new discriminating runtime hypothesis; no session fabrication or repeated QEMU reconstruction is justified by the current evidence. Until the original call executes, do not claim `NATIVE_WRAPPER_EXECUTED`, full stock-path equivalence, or Honda Type111 integration.
