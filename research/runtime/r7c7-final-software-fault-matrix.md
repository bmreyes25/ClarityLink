# R7C7 final software fault matrix

| Software row | Evidence | Status |
|---|---|---|
| Owned API17 AVD creation, identity, install, cleanup | API17 / Android 4.2.2 / x86 / Dalvik; unique process/serial; harness cleanup | PASS |
| Production Type110/Type111 socket to receiver to H.264 to Android Surface | full decode/post on both streams plus 100-cycle run | PASS |
| Type111 timeout/refusal/peer-close/malformed/truncated/zero/oversized/wrong-stream/wrong-generation | production Android socket adapter fault matrix; Type110 follow-up remains usable | PASS |
| Type110 refusal policy | session-global teardown verified | PASS |
| Local port collision | client-only adapter uses ephemeral local bind; no local server bind path | NOT_APPLICABLE |
| Type110/Type111 Surface loss | session/global and stream-local semantics verified; repeated Type111 stress | PASS |
| Presentation dismissal | Type111 closes while Type110 retains output; 25 repetitions | PASS |
| SETUP and decode cancellation | deterministic cancellation; 25 Type111 decode cancellation repetitions | PASS |
| Read/write shutdown | active checkpointed operations interrupted and joined | PASS |
| Activity destruction after cumulative stress | full combined run plus independent 25-repeat Activity run | PASS |
| JNI pending-exception handling and class lookup probes | fail-closed probes and exception closure in integrated suite | PASS |
| Production JNI global refs / weak refs | no persistent application object references are used by these synchronous adapter paths | NOT_APPLICABLE |
| Native-to-Java worker callbacks | no native worker calls into Java; Java owns workers and joins them | NOT_APPLICABLE |
| API17 ARMv7 production artifact | NDK r23c build; ELF32 ARM EABI5; unknown API17 imports none | PASS |
| Honda, iPhone/MFi, physical USB and vehicle runtime | outside offline software scope and not exercised | EVIDENCE_REQUIRED |
