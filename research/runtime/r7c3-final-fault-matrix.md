# R7C3 final software fault matrix — incomplete

| Software fault | Evidence in this attempt | Result |
|---|---|---|
| Host native loopback socket | `tools/test_r7c_socket_host.sh` | PASS (host only) |
| JNI native socket → LAB frame → ReceiverGeneration on Dalvik | Added test seam; APK could not rebuild without JDK | PARTIAL |
| JNI raised Java exception and failed lookup | Added test-only probes; APK could not rebuild | PARTIAL |
| JNI global refs / weak refs | No production references exist | NOT_APPLICABLE (`NO_PRODUCTION_GLOBAL_JNI_REFS`, `NO_PRODUCTION_WEAK_JNI_REFS`) |
| Native-to-Java worker callback | No production path exists | NOT_APPLICABLE (`NO_NATIVE_TO_JAVA_WORKER_CALLBACK_PATH`) |
| Framework callback/process-stop races | Not added/run in this attempt | PARTIAL |
| R7C1 host receiver/surface integration | `tools/test_r7c1_integrated.sh` | PASS (host simulation) |
| API17 ARMv7 build/import audit | Rebuilt; known stubs only, zero unknown | PASS (build evidence only) |
| Repository pytest suite | `tools/run_tests.sh` | NOT RUN: `pytest` unavailable |

Honda, physical USB, real iPhone, MFi, and vehicle rows remain `EVIDENCE_REQUIRED` and do not block the software gate. The software matrix is not closed. The socket and JNI rows cannot be promoted from build/source evidence to Android runtime PASS.
