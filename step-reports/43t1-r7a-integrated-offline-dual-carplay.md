# 43T1-R7A — integrated offline dual-CarPlay receiver

Date: 2026-10-06. Starting HEAD: `c254d7f6172dbd45bb1cd6a87b10bcb4cd96d811`. Worktree branch: `architecture/r7a-integrated-offline-dual-carplay`.

## Decision

**Result: `R7A_INTEGRATED_SYNTHETIC_DUAL_STREAM_PASS`.** A single explicitly synthetic authenticated session exchanged the existing bounded `/info` shape, completed SETUP for Type110 and Type111, received independent loopback media, decoded actual H.264 access units with host FFmpeg, delivered differently colored decoded 800×480 frames to separate outputs, and cleared both outputs and resources on disconnect. The demo wrote `display0-type110.png` and `display1-type111.png` as deterministic verification artifacts when invoked.

The path is `MODEL_ONLY`. The Type111 request order in existing lab evidence is `CURRENT_IOS_LAB_CONFIRMED`; the R7A SETUP acceptance and synthetic media are not. The output and software decode are `HOST_CONFIRMED`; existing external receiver examples stay `EXTERNAL_PRIOR_ART`. Honda Display1 admission, physical safe area, warning coexistence, target ABI compatibility, and real Type111 security are `UNKNOWN` or `EVIDENCE_REQUIRED`. Nothing here establishes iOS acceptance or genuine MFi authentication.

## Implementation and findings

- Extended the existing generation-scoped `Receiver`; did not create a parallel receiver framework. It owns both listeners, per-stream IDs, security providers, decoders, output sinks and cleanup.
- Added a synthetic authentication authority that labels its proof `MODEL_ONLY`, a complete `/info` exchange path, primary and secondary media/decode/output paths, configurable output dimensions, and neutral USB/iAP2, control, audio, input, display and process adapter contracts.
- Added synchronized state transitions and failure rollback. Non-lab Type110 media and default Type111 security fail closed. Only generated clear media reaches the lab provider. No speculative production cryptography was added.
- ECC architecture review found an original-resource rollback edge where newly allocated Type110 decoder/security resources could be closed before being retained on Type111 failure. Corrected by retaining primary ownership only when primary initialization completed.
- ECC resource review found primary teardown dropped references after `close()` failure. Corrected to retain failed resources for retry and leave cleanup incomplete/visible.
- ECC authentication review found host Type110 media could otherwise be passed as clear bytes. Added `EvidenceRequiredPrimarySecurity`, so SETUP compatibility does not silently imply media-security readiness.
- ECC thread-safety review found unguarded receiver state transitions; added a re-entrant owner lock around public lifecycle, setup, accept, receive and snapshot operations.
- Parser/security review confirms finite message lengths, opcode allowlists, generation checks, loopback-only listener binding, per-stream connection IDs, fail-closed crypto, and no credentials or secrets in the new fixtures. FFmpeg inputs, timeouts, output sizes and dimensions are bounded.
- Dependency provenance: no new Python runtime or test dependency. Tests use the already declared `pytest`, `cryptography`, and `unicorn` requirements. Host decoding uses the installed FFmpeg CLI (`9.0.2` observed locally); FFmpeg/libx264 availability is an environment prerequisite, not a bundled dependency.

## Acceptance and verification

- Integrated session: **PASS**; one session and simultaneous Type110+Type111 state.
- `/info` + SETUP: **PASS** with generated identity/capability fixtures; no current iOS response claim.
- Independent decoded outputs: **PASS**, one valid PNG frame each, each 800×480, timestamps 10/20 and distinct image content.
- Stream order/single-stream cases: **PASS** for Type111→Type110, Type110→Type111, Type110-only and Type111-only.
- Type111 failure isolation, Type110 setup failure, fail-closed media security, malformed/truncated/unsupported input, decoder failure, listener disconnect, stale generation, duplicate IDs, partial initialization, repeated close and post-teardown delivery: **PASS**.
- Lifecycle: **PASS**, 100 complete reconnect/disconnect cycles, unique generation each cycle, and zero sessions, listeners, security providers, decoders, displayed frames or uncleared displays after each close.
- Existing and complete repository suite: **901 passed, 14 skipped**. The project runner also passed its self-locator smoke (3 passed) and all configured JavaScript simulator checks. Capture-backed replay scripts were skipped because their private fixtures are not CI inputs.
- Repository health: **PASS**, 654 Markdown files, 139 indexed reports, zero curated broken links and zero forbidden tracked extensions.
- `git diff --check`: **PASS**.
- Hosted Offline CI and CodeQL: **PENDING** until the implementation commit is pushed and the PR runs on that exact head. No prior-run result is carried forward.

## Readiness and remaining blockers

Type110 host readiness: `IMPLEMENTED_HOST_TESTED` for synthetic SETUP/listener/decode/output only; production media security is `BLOCKED`. Type111 host readiness: `IMPLEMENTED_HOST_TESTED` for synthetic request/listener/media/decode/output using explicit lab security; actual Type111 security is `BLOCKED`. Media is host-tested for generated H.264 only. Display readiness is host-tested at configurable 800×480; Honda Display0/Display1 admission and cluster safe area remain unknown. Authentication readiness is synthetic only (`MODEL_ONLY`); real MFi/iPhone authority is `EVIDENCE_REQUIRED`. Honda compatibility is `EVIDENCE_REQUIRED`/`UNKNOWN` for unimplemented adapters.

R6's hardware-gated real-session chronology is preserved. `R7_OFFLINE_IMPLEMENTATION_FIRST` changes only sequencing: CPC200 is no longer required to continue offline receiver, media, decoder, host display, integration and R7B build work. See [R7 host-to-Honda boundary inventory](../research/runtime/r7a-host-honda-boundary-inventory.md). No CPC200, iPhone, Honda, ADB, APK, `jmcs` binary, CAN, vehicle framebuffer, vehicle firmware or startup configuration was accessed or changed.

## Next milestone

Recommend **`GO_FOR_R7B_ANDROID_API17_ARMV7_NATIVE_BUILD`**. Port the host contracts and deterministic protocol fixtures to a reproducible API17/ARMv7 native build, pin the cross-toolchain and dependencies, and establish decoder/media buffer ownership on the target ABI. Keep real Type111 crypto, Honda authentication/USB, display admission and vehicle operation as separate evidence-gated blockers.
