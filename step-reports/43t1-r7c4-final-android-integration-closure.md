# 43T1 — R7C4 final Android integration closure

**Starting HEAD:** `0804bc0b3c6f6b7a63483562ce539eaa8550d778`  
**Decision:** `R7C_FRAMEWORK_RACE_BLOCKED`  
**R7D entry:** CLOSED  
**Next action:** finish deterministic API17 framework/process race and remaining fault-matrix coverage, then reverify one exact final head.

## Completed in this attempt

- Recovered a pinned user-local Temurin JDK 17 and used the existing project `.venv`; no tracked dependency versions changed. Details: [JDK provenance](../research/runtime/r7c4-jdk-toolchain-recovery.md) and [test environment](../research/runtime/r7c4-test-environment-recovery.md).
- Rebuilt the diagnostic API17 x86 test APK and ran it on the isolated Android 4.2.2/API17 x86 Dalvik emulator. The runner returned `RESULT=PASS`, `CYCLES=100`.
- The test-only native POSIX socket JNI path used numeric loopback and fragmented separate LAB Type110 and Type111 envelopes. Both were delivered through `ReceiverGeneration` to their respective decoder/Surface paths; JNI return and peer completion succeeded. JNI-created and failed-lookup exceptions were observed on Dalvik. Native socket descriptor count returned to its measured baseline (4 before and 4 after); native project counters returned to zero.
- The 100-cycle harness reported native owner counters zero per cycle; PSS varied from 6,273–6,859 KiB at sampled cycles and was 6,454 KiB after GC; native heap allocation stayed approximately 10.58 MB. These cycles do not include a native socket in every cycle.
- Full Python suite: 902 passed, 14 skipped. Host socket adapter, Java policy, R7C1 integration, repository health, and whitespace checks passed where the required tools were present.

## ECC review and remaining closure gap

The R7C3 socket and JNI source seams now have actual Dalvik execution evidence. The socket runtime path covers one successful fragmented Type110 delivery only; it does not cover the required timeout, peer-close, shutdown-during-I/O, refused/colliding port, malformed/oversized frame, stale owner, and Type111 socket-failure isolation matrix. The 100-cycle test uses synthetic ingest instead of a native socket in every cycle.

The current test activity does not implement deterministic barriers for SurfaceHolder callback/post races, Presentation dismissal, stop during setup/decode, or Activity destroy during dual-stream/socket/audio activity. This is the narrowest release blocker: **`R7C_FRAMEWORK_RACE_BLOCKED`**. The requested socket failure-isolation matrix, per-cycle native socket coverage, and remaining software fault/resource closure also remain incomplete. No R7D work or merge is authorized by the acceptance rule until all R7C gates pass.

The final R7C4 source was not rebuilt for ARMv7 because pinned NDK r23c is absent, and exact-head Offline CI/CodeQL have not run on an R7C4 commit. These are additional unmet acceptance rows, not evidence of a software failure. R7C3 hosted results on `0804bc0` do not verify this uncommitted working tree.

No Honda, vehicle, physical-device ADB, real iPhone, MFi, authentication hardware, or live CarPlay action occurred. Honda-specific unknowns remain evidence-gated and are not used to hold the software milestone open.
