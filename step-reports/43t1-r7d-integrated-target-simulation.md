# 43T1 R7D integrated target simulation

**Starting HEAD:** `f9ef5fa3f24ed89b32d0eddf62b1065fbef66562` (R7C merge commit)
**Branch:** `architecture/r7d-integrated-target-simulation`
**Decision:** `R7D_INTEGRATED_TARGET_SIMULATION_PASS_PENDING_EXACT_HEAD_GATES`

## Scope

Offline API17/Android 4.2.2 x86 Dalvik emulator; synthetic media; actual production AndroidSocketAdapter, ReceiverGeneration, H.264 decoding, Android Surfaces, Presentation Surface, and AudioTrack. No Honda, physical Android device, vehicle, real iPhone, or MFi credential is involved.

## Results so far

- R7C PR #17 merged after exact-head Offline CI and CodeQL passed.
- Type111 restart stress: 100/100 passes; 200 Type110 continuity frames; secondary clear and owner checks pass.
- The initial restart run exposed a latched Type111 setup cancellation flag after stream closure. ReceiverGeneration now clears that flag under lock on completed Type111 teardown; rerun passed.
- Corrected long run: 30:00.180, 25,932 frames per stream, 14.405 FPS, 28,073 missed 30-FPS schedule slots, and zero delivery failures. Every native owner returned to zero, FD count returned to baseline 5 (delta 0), and the race controller was idle. PSS ranged 8,623–15,470 KiB; native heap stayed 13,344,968–13,345,112 bytes. The measured throughput is below the near-30-FPS target and is recorded as a performance limitation.
- Display recreation: 25/25 Surface destroy/recreate and 25/25 Presentation dismiss/recreate cycles passed with Type110 continuity; synthetic display removal/re-add was not exercised.
- Network recovery: production AndroidSocketAdapter fragmentation/delay/timeout/peer-close/refusal cases and 25 reconnect cycles passed with Type111-local versus Type110-global scope checks.
- Decoder stress: 25 repeated IDRs, five malformed Type111 NALs, one truncated Type111 NAL, Type110 isolation, and six Type111 decoder re-creations passed.
- Churn: 500/500 synthetic receiver sessions returned native owner counters to zero and maintained the FD baseline. PSS sampled 6,889–7,217 KiB after warmup in the churn test.
- Repository suite: 901 passed, 15 skipped; self-locator and simulator checks passed. Socket and integrated adapter ASan/UBSan and TSan runs passed.
- API17 x86 APK build and API17 ARMv7 import audit passed. ARMv7 SHA-256: `ebba888796584d583493194155a0f997e6ac279f5da89e1271ac4030509d19c9`; test-only bridge symbols were absent.
- Repository health and `git diff --check` passed.

## Final local gate status

All requested local R7D runtime and repository checks pass. The 14.405 FPS result remains below the near-30-FPS target and is a documented performance limitation; all per-stream processing continued for the full duration without delivery failure or resource leakage. The R7D PR must receive exact-head Offline CI and CodeQL before R7E entry opens.

Post-long-run R7C API17 default regression also passed: 100 cycles; Type110 and Type111 H.264 Surface posts; responsive main-looper heartbeat; cumulative race suite with 25 Type111 Surface, 25 Presentation, and 25 peer-close cases; Activity destruction; `RESULT=PASS`, `ERROR=NONE`.

Repository suite: 901 passed, 15 skipped. Host socket ASan/UBSan and TSan passed; integrated adapter ASan/UBSan and TSan passed. API17 x86 build passed. API17 ARMv7 build/import audit had zero unknown imports and excluded both test-only bridge methods; artifact SHA-256 `ebba888796584d583493194155a0f997e6ac279f5da89e1271ac4030509d19c9`. Repository health and `git diff --check` passed.

Next: final clean diff/status review, commit/push, open the R7D PR, then verify Offline CI and CodeQL on that exact head. Do not open R7E entry until those checks pass.

R7D does not establish Honda factory restoration, Honda display behavior, real CarPlay, or MFi authority. See linked `research/runtime/r7d-*` evidence.
