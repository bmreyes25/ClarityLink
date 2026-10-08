# R7C3 JNI exception/reference closure — incomplete

The production JNI bridge owns no global or weak JNI references and creates no native-to-Java worker callback. Its Java references are call-local; the `ANativeWindow_fromSurface` temporary native owner is released after the sink takes its own reference. Classifying these paths does not require adding artificial references or worker threads.

This attempt added test-build-only probes for an exception raised at a JNI boundary and a failed `FindClass`; the methods are in the test APK source set and native test exports are diagnostic-build gated. The x86 native library compiled, but the test APK could not be rebuilt because the host has no Java runtime/JDK (`javac`: “Unable to locate a Java Runtime”). No Dalvik result is claimed for these probes.

## Explicit policy

- `PREEXISTING_JAVA_EXCEPTION`: preserve it, stop dependent JNI work, perform only legal native cleanup, and return.
- `NATIVE_CXX_EXCEPTION`: catch before crossing the JNI/C ABI; translate only when no Java exception is pending.
- `NEW_JAVA_EXCEPTION_FROM_HELPER`: detect it, stop dependent work, preserve it, and perform native-only cleanup.
- No code clears an unrelated Java exception.

## ECC findings

| Finding | Risk | Fix/status | Verification |
|---|---|---|---|
| Pending-exception legality needs VM evidence | Illegal JNI follow-on operations can corrupt error propagation | Probe returns immediately after `ExceptionCheck`; only local-ref cleanup is used after throwing | Source review; Dalvik execution pending |
| Repeated local refs could exhaust Dalvik's local table | Runtime failure during repeated Surface/class/helper operations | Existing production refs are entrypoint-local; no persistent global refs exist | Prior R7C2 cycles exercised Surfaces; new test repeats and lookup injection unverified |
| Native global/weak refs and callback workers may be assumed incorrectly | Invented lifecycle obligations obscure actual ownership | `NO_PRODUCTION_GLOBAL_JNI_REFS`, `NO_PRODUCTION_WEAK_JNI_REFS`, `NO_NATIVE_TO_JAVA_WORKER_CALLBACK_PATH` | Confirmed by current source inspection |

**Decision: `R7C_JNI_EXCEPTION_REFERENCE_BLOCKED`.** Required Dalvik assertions for helper-thrown exceptions, pending exception preservation across dependent work, repeated local-ref operations, and shutdown-after-exception remain unexecuted. No global or weak reference test objects were invented.
