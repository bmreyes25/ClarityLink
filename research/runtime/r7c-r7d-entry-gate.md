R7C3 attempt (2026-10-07) does not change the decision: `R7C_INTEGRATION_PARTIAL`, R7D `CLOSED`. A test-only socket/JNI seam and exception probes compile in the x86 native library, but APK/Dalvik verification is blocked by absent JDK. Deterministic framework races, full software fault/resource closure, fresh 100-cycle test with native socket, and exact-head CI/CodeQL remain pending. See [R7C3 decision](r7c3-r7d-entry-decision.md).

# R7C closure → R7D entry gate

R7D is blocked until every software gate below is evidenced on an exact PR head. Honda runtime evidence is not required for this software gate and cannot be inferred from host simulation.

| Gate | Current R7C2 evidence | Status |
|---|---|---|
| JNI lifecycle on real Dalvik bridge | Actual API17 x86 entrypoints and R7C4 pending/lookup probes; local-reference stress and broader exception cleanup cases incomplete | PARTIAL |
| Surface lifecycle and race contract | Actual ANativeWindow posts and invalidation; framework callback/post race injection incomplete | PARTIAL |
| Full Android/JNI all-adapter harness | R7C4 successful native socket delivery for both streams through receiver/H.264/Surface; socket failure matrix and per-cycle socket coverage incomplete | PARTIAL |
| Full fault matrix | Actual-runtime cases catalogued; exception and deterministic stop/callback rows remain open | BLOCKED |
| Type111 isolation | Dalvik native Surface invalidation retains Type110; host malformed-media/display failures also pass | PASS |
| 100 integrated Android receiver cycles | 100 API17 Dalvik x86 synthetic-ingest cycles, actual H.264 output to two Surfaces | PASS_X86 |
| Per-cycle native resource zero | Every Android cycle asserted native diagnostics zero; Java adapter close states checked separately | PASS_X86 |
| JNI ASan/UBSan/TSan coverage | Opaque table/receiver/surface/socket host tests pass; Android VM itself not sanitizer-instrumented | PASS_HOST / PARTIAL_RUNTIME |
| API17 Java build | API17 compile and policy harness pass | PASS |
| API17 ARMv7 JNI/native build/import audit | API17 / armeabi-v7a artifact and imports pass | PASS |
| R7A regressions | Full Python suite pass | PASS |
| R7B native regressions | Dual decode and 100 receiver cycles pass | PASS |
| Repository health / diff check | Local checks pass on current staged work | PASS |
| Offline CI / CodeQL exact final head | Required after push | PENDING |

R7D may start only when all blocked/partial/pending software gates are closed on one exact final HEAD. R7C4 now has successful Dalvik evidence for one native Type110 loopback socket delivery, JNI exception probes, and a 100-cycle synthetic-ingest harness. Deterministic framework races, the full socket/fault matrix, per-cycle native socket coverage, final ARMv7 build/import audit, and exact-head hosted checks remain open. Decision: `R7C_FRAMEWORK_RACE_BLOCKED`; next action is to complete those R7C gates. This gate does not authorize a Honda, physical-device ADB, vehicle, or live CarPlay action.

## R7C5 correction (2026-10-08)

The exact NDK r23c ARMv7/API17 rebuild and API17 import audit now pass locally (zero unknown imports). The repository suite, API17 Java/APK build, and host socket/R7C1 sanitizer runs also pass. The R7C5 attempt did not run the API17 emulator because AVD creation fails on missing API17 image `devices.xml`; deterministic framework races, production native socket fault/cycle coverage, full per-cycle resource accounting, and exact-head hosted checks remain open. The decision remains `R7C_FRAMEWORK_RACE_BLOCKED`; see [R7C5 entry decision](r7c5-r7d-entry-decision.md) and [R7C5 closure report](../../step-reports/43t1-r7c5-final-software-closure.md).
# R7C6 decision update (2026-10-08)

R7C remains `R7C_FRAMEWORK_RACE_BLOCKED`; R7D entry remains CLOSED. API17
owned-AVD smoke, selected deterministic races, and the prior 100-cycle native
socket run have evidence, but Type110 framework Surface destruction, full
Activity destruction, race repetitions, complete Dalvik socket matrix, final
current-code run, fresh ARMv7/sanitizer checks, and exact-head hosted checks
are not complete. See `r7c6-r7d-entry-decision.md` and the R7C6 step report.

## R7C7 software closure (2026-10-08)

The API17 owned-emulator cumulative Activity blocker is closed: the test runner holds process liveness with a guard Activity, awaits lifecycle off-main, and 25/25 current-code repetitions reach `onDestroy`. The production Dalvik socket fault matrix and socket-inclusive 100-cycle combined suite pass. Final evidence is indexed in the [R7C7 report](../../step-reports/43t1-r7c7-final-framework-race-closure.md), [socket matrix](r7c7-native-socket-fault-matrix.md), [combined run](r7c7-combined-acceptance-run.md), and [100-cycle report](r7c7-final-100-cycle-runtime.md).

All software gates are locally evidenced. Final commit/push, exact-head Offline CI and CodeQL, and PR #17 merge remain prerequisites. R7D starts from the merge commit only. Honda/iPhone/MFi/physical-device evidence remains separate and unclaimed.

## Exact-head checks and merge result

R7C implementation HEAD `f24255c58ea000255c37d1dea28e5b26a569745b`: Offline CI PASS, CodeQL PASS. PR #17 merged at `f9ef5fa3f24ed89b32d0eddf62b1065fbef66562`. R7C decision `R7C_HONDA_ADAPTER_LAYER_OFFLINE_PASS`; R7D entry opened for offline simulation. Honda-specific/real-CarPlay evidence remains unresolved.
