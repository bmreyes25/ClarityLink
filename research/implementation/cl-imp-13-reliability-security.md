# CL-IMP-13 reliability and security validation — 2026-10-13

## Result

CL-IMP-13 adds deterministic malformed-frame fuzzing, repeated unified-runtime lifecycle churn, and concurrent stream retention checks on top of the existing receiver, decoder, renderer, Binder and native tests. Production Honda integration remains disabled; all receiver media is fixture-based synthetic content.

## Added validation

- **Framing fuzz:** 512 seeded malformed Type110/current-Type111 header cases across two framing profiles. Invalid lengths and opcodes reject before body reads; no allocation based on invalid lengths.
- **Runtime churn:** 32 start/stop cycles with both Type110 and Type111 workers connected. Every cycle ends with zero sessions, listeners, security contexts, decoders, displayed frames, uncleared displays, and live stream workers.
- **Concurrent retention:** 24 fixture frames are delivered across two independent streams. Each display retains only its latest frame, PNG outputs remain within the established 8 MiB decode output cap, and runtime event history stays within its 128-event bound.
- Existing malformed H.264/authentication failure/secondary-only teardown, warning preemption, generation fencing, display/Surface cleanup, Binder process disconnect and API17 emulator checks continue to pass.

## Validation results

- Focused runtime additions: 3 passed.
- Full configured offline suite: 1,428 passed, 14 skipped; self-locator smoke and simulator JavaScript checks passed.
- Native integrated adapter with AddressSanitizer + UndefinedBehaviorSanitizer: passed, including Surface and opaque handle tests, actual H.264 fixture decode and 100 lifecycle cycles with zero resources after each cycle.
- Native integrated adapter with ThreadSanitizer: passed; no race report.
- API17 emulator Presentation/content and MediaCodec decoder validations remain valid from CL-IMP-12. CL-IMP-13 changes no Android or native source; no redundant emulator run was needed.
- Repository health and `git diff --check`: passed.
- ECC reliability/security checklist review: no blocking finding. Reviewed bounded fuzz inputs, worker shutdown ownership, retained frame limits, event bounds, and sanitizer results. This was an in-session checklist review, not an independent reviewer attestation.

The first churn-test draft closed workers while they were still waiting in listener admission, making the test wait for the accept timeout. That run was interrupted. The test now waits for both workers to connect before shutdown, then verifies cleanup; no timeout was extended and no implementation behavior was hidden.

## Evidence limits and remaining work

These are host, sanitizer and isolated API17 emulator results. They do not validate Honda process/display admission, Honda warning priority, authentic iPhone authentication, genuine Type111 security, physical scanout, or vehicle reliability. No Honda or live-iPhone operations occurred. CL-IMP-14 must reconcile the entire campaign and list remaining deployment requirements; further production evidence requires separate authorization.
