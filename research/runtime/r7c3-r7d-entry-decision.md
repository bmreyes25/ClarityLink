# R7C3 → R7D entry decision

**Decision: `R7C_INTEGRATION_PARTIAL`**
**R7D entry: CLOSED**
**Next action: `GO_FOR_R7C_INTEGRATION_CLOSURE`**

Historical R7C3 snapshot: the attempt added a test-only native socket/JNI frame path and exception probes. At that snapshot, the x86 JNI library compiled, the production ARMv7/API17 library rebuilt, the import audit reported only expected API17 stubs and zero unknown imports, and host socket plus R7C1 integration harnesses passed. Its APK/Dalvik and environment statements were current only at that snapshot; see the R7C4 correction below.

**R7C4 correction (2026-10-07):** JDK 17 and the existing pytest environment were restored locally. The R7C4 APK ran on API17 Dalvik; separate fragmented Type110 and Type111 native socket→receiver→H.264→Surface deliveries, JNI exception probes, and a 100-cycle synthetic-ingest lifecycle harness passed. This does not cover the full socket fault matrix, per-cycle native socket, or deterministic framework races. The R7C4 source remains uncommitted at this snapshot, so R7C3's exact-head Offline CI and CodeQL PASS on `0804bc0b3c6f6b7a63483562ce539eaa8550d778` do not apply to it. See [R7C4 closure report](../../step-reports/43t1-r7c4-final-android-integration-closure.md).

GitHub PR #17 confirms head `0804bc0b3c6f6b7a63483562ce539eaa8550d778` is OPEN/CLEAN with Offline CI and all CodeQL checks SUCCESS. This is the R7C3 pushed head only; the current R7C4 working tree has no exact-head hosted result.

Honda-specific unknowns remain later evidence gates and were not used to decide this software status. No Honda, vehicle, real iPhone, MFi, or physical USB action occurred.
