R7C3 attempt: test-only native socket and JNI exception seams are present in the worktree, but updated API17 APK/Dalvik execution did not occur (JDK unavailable). No readiness classification is promoted; R7C remains partial and R7D remains closed. See [`R7C3 decision`](r7c3-r7d-entry-decision.md).

# R7C Honda adapter readiness

| Adapter | Classification | Honda status |
|---|---|---|
| JNI | ANDROID_API17_DALVIK_RUNTIME_CONFIRMED_X86, ANDROID_ARMV7_BUILD_CONFIRMED | EVIDENCE_REQUIRED |
| Display0 | ANDROID_API17_DALVIK_RUNTIME_CONFIRMED_X86, ANDROID_API_DOCUMENTED | EVIDENCE_REQUIRED |
| Display1 enumeration | ANDROID_API17_DALVIK_RUNTIME_CONFIRMED_X86, ANDROID_API_DOCUMENTED | HONDA_READ_ONLY_OBSERVED (logical display evidence only) |
| Display1 Presentation | ANDROID_API17_DALVIK_RUNTIME_CONFIRMED_X86, ANDROID_API_DOCUMENTED | EVIDENCE_REQUIRED |
| Display1 Surface | ANDROID_API17_DALVIK_RUNTIME_CONFIRMED_X86, ANDROID_ARMV7_BUILD_CONFIRMED | EVIDENCE_REQUIRED |
| Display1 actual Honda admission | EVIDENCE_REQUIRED | EVIDENCE_REQUIRED |
| Safe area | UNKNOWN | EVIDENCE_REQUIRED |
| Warning coexistence | UNKNOWN | EVIDENCE_REQUIRED |
| Socket | IMPLEMENTED_OFFLINE, ANDROID_ARMV7_BUILD_CONFIRMED | EVIDENCE_REQUIRED |
| USB | IMPLEMENTED_OFFLINE, ANDROID_API_DOCUMENTED | EVIDENCE_REQUIRED |
| iAP2 | IMPLEMENTED_OFFLINE | EVIDENCE_REQUIRED |
| Authentication | IMPLEMENTED_OFFLINE | EVIDENCE_REQUIRED |
| Audio | IMPLEMENTED_OFFLINE, ANDROID_API_DOCUMENTED | EVIDENCE_REQUIRED |
| Touch | IMPLEMENTED_OFFLINE | EVIDENCE_REQUIRED |
| Steering controls | UNKNOWN | EVIDENCE_REQUIRED |
| Siri input | IMPLEMENTED_OFFLINE | EVIDENCE_REQUIRED |
| Process lifecycle | IMPLEMENTED_OFFLINE, ANDROID_API_DOCUMENTED | EVIDENCE_REQUIRED |
| Restoration | IMPLEMENTED_OFFLINE | EVIDENCE_REQUIRED |
| Type110 integration | IMPLEMENTED_OFFLINE | EVIDENCE_REQUIRED |
| Type111 integration | IMPLEMENTED_OFFLINE | EVIDENCE_REQUIRED |
| ARMv7/API17 | ANDROID_ARMV7_BUILD_CONFIRMED | EVIDENCE_REQUIRED |
| Honda executable | EVIDENCE_REQUIRED | EVIDENCE_REQUIRED |
| JNI lifecycle | ANDROID_API17_DALVIK_RUNTIME_CONFIRMED_X86 (entrypoints/stale handles); pending-exception injections incomplete | EVIDENCE_REQUIRED |
| JNI race coverage | IMPLEMENTED_OFFLINE (table allocator concurrency); Dalvik callback race coverage partial | EVIDENCE_REQUIRED |
| Surface lifecycle | ANDROID_API17_DALVIK_RUNTIME_CONFIRMED_X86 (actual ANativeWindow posts) | EVIDENCE_REQUIRED |
| Surface race coverage | IMPLEMENTED_OFFLINE plus runtime invalidation; framework callback/post race injection incomplete | EVIDENCE_REQUIRED |
| Full adapter integration | ANDROID_API17_DALVIK_RUNTIME_CONFIRMED_X86 (selected Java adapters + receiver/H.264/Surface) | EVIDENCE_REQUIRED |
| Fault matrix | IMPLEMENTED_OFFLINE partial; actual Dalvik cases in R7C2 matrix | EVIDENCE_REQUIRED |
| 100-cycle full integration | ANDROID_API17_DALVIK_RUNTIME_CONFIRMED_X86; per-cycle native counters zero | EVIDENCE_REQUIRED |
| Sanitizer coverage | IMPLEMENTED_OFFLINE host core/table/receiver ASan/UBSan/TSan | EVIDENCE_REQUIRED |
| Resource accounting | IMPLEMENTED_OFFLINE explicit host oracle; Android runtime counts absent | EVIDENCE_REQUIRED |
| Restoration accounting | IMPLEMENTED_OFFLINE host owners only | EVIDENCE_REQUIRED |

Generic Java API17 compilation, API17 Dalvik x86 execution, and ARMv7/API17 JNI shared-library build are separate evidence levels; none establishes Honda execution. R7C2 software integration remains partial because actual native Android socket JNI runtime, pending-exception injection, and deterministic framework callback/stop races are incomplete. No status uses HONDA_COMPATIBLE.

R7C1/R7C2 evidence: [`runtime baseline`](r7c2-android-runtime-baseline.md), [`Dalvik/JNI`](r7c2-dalvik-jni-runtime.md), [`Surface`](r7c2-android-surface-runtime.md), [`secondary display`](r7c2-secondary-display-runtime.md), [`Java adapter integration`](r7c2-java-adapter-integration.md), [`fault matrix`](r7c2-android-fault-matrix.md), and [`resource accounting`](r7c2-runtime-resource-accounting.md). R7C remains partial until software gaps in the [`R7D entry gate`](r7c-r7d-entry-gate.md) are closed.

R7C5 update: local NDK r23c ARMv7/API17 build and import audit pass; deterministic Surface/Presentation/Activity races, Android native socket faults and every-cycle socket coverage, and complete per-cycle owner accounting remain unproven. See [R7C5 ARM build](r7c5-armv7-final-build.md), [race status](r7c5-framework-race-closure.md), and [native socket status](r7c5-native-socket-runtime-closure.md). No Honda readiness classification is promoted.
# R7C6 update (2026-10-08)

API17 generic owned-AVD smoke now passes. Selected Type111 Surface and
Presentation teardown races passed on Dalvik and Type110 remained usable.
R7C is still blocked on the remaining framework races and full fault matrix;
see `r7c6-final-software-fault-matrix.md`.

## R7C7 software gate update — 2026-10-08

Owned API17/Dalvik software validation now closes the cumulative Activity lifecycle and production native socket fault matrix; the combined socket-inclusive 100-cycle run and independent 25-repeat Activity run pass. See [R7C7 closure](../../step-reports/43t1-r7c7-final-framework-race-closure.md). This does not resolve Honda-specific or real-CarPlay readiness: those rows remain evidence-required.
