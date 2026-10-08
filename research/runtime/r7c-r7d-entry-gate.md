R7C3 attempt (2026-10-07) does not change the decision: `R7C_INTEGRATION_PARTIAL`, R7D `CLOSED`. A test-only socket/JNI seam and exception probes compile in the x86 native library, but APK/Dalvik verification is blocked by absent JDK. Deterministic framework races, full software fault/resource closure, fresh 100-cycle test with native socket, and exact-head CI/CodeQL remain pending. See [R7C3 decision](r7c3-r7d-entry-decision.md).

# R7C closure → R7D entry gate

R7D is blocked until every software gate below is evidenced on an exact PR head. Honda runtime evidence is not required for this software gate and cannot be inferred from host simulation.

| Gate | Current R7C2 evidence | Status |
|---|---|---|
| JNI lifecycle on real Dalvik bridge | Actual API17 x86 JNI entrypoints, stale/invalid handle and create/release exercised; pending-exception/reference fault injections incomplete | PARTIAL |
| Surface lifecycle and race contract | Actual ANativeWindow posts and invalidation; framework callback/post race injection incomplete | PARTIAL |
| Full Android/JNI all-adapter harness | Actual receiver/H.264/Surface and selected Java adapters run; native Android POSIX socket adapter not runtime-integrated | PARTIAL |
| Full fault matrix | Actual-runtime cases catalogued; exception and deterministic stop/callback rows remain open | BLOCKED |
| Type111 isolation | Dalvik native Surface invalidation retains Type110; host malformed-media/display failures also pass | PASS |
| 100 integrated Android receiver cycles | 100 API17 Dalvik x86 cycles, actual H.264 output to two Surfaces | PASS_X86 |
| Per-cycle native resource zero | Every Android cycle asserted native diagnostics zero; Java adapter close states checked separately | PASS_X86 |
| JNI ASan/UBSan/TSan coverage | Opaque table/receiver/surface/socket host tests pass; Android VM itself not sanitizer-instrumented | PASS_HOST / PARTIAL_RUNTIME |
| API17 Java build | API17 compile and policy harness pass | PASS |
| API17 ARMv7 JNI/native build/import audit | API17 / armeabi-v7a artifact and imports pass | PASS |
| R7A regressions | Full Python suite pass | PASS |
| R7B native regressions | Dual decode and 100 receiver cycles pass | PASS |
| Repository health / diff check | Local checks pass on current staged work | PASS |
| Offline CI / CodeQL exact final head | Required after push | PENDING |

R7D may start only when all blocked/partial/pending software gates are closed on one exact final HEAD. R7C2 closes the actual API17 Dalvik/JNI/Surface gap but leaves native Android POSIX socket runtime, VM exception injection, and deterministic Android callback/stop fault rows open. Current decision remains `R7C_INTEGRATION_PARTIAL`; next action stays `GO_FOR_R7C_INTEGRATION_CLOSURE`. If fully closed, next action may be `GO_FOR_R7D_INTEGRATED_TARGET_SIMULATION`. This gate does not authorize a Honda, physical-device ADB, vehicle, or live CarPlay action.
