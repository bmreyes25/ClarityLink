# R7C2 decision and R7D entry

## Decision

R7C2 closes the central R7C runtime gap: actual API17 Dalvik executes the JNI library, API17 DisplayManager/Presentation and Android Surfaces, native ANativeWindow rendering, actual H.264 Type110/Type111 output, selected Java adapters, and 100 per-cycle native cleanup checks. Classification is `ANDROID_API17_DALVIK_RUNTIME_CONFIRMED_X86`; ARMv7 remains build-only.

R7C remains `R7C_INTEGRATION_PARTIAL`. The full acceptance gate is not met: JNI pending-exception/reference fault injection, native Android socket-adapter runtime use, and the deterministic Android callback/stop fault matrix remain incomplete. This is a software integration gap, not a Honda requirement. Decision does not authorize R7D.

## Gate

`R7D entry gate: CLOSED`. Next action remains `GO_FOR_R7C_INTEGRATION_CLOSURE`.

To close R7C, add the native socket adapter to the Dalvik loopback path; inject/check Java exception state and owner destruction cases through real JNI; exercise Android callback/stop races using barriers; and close the software fault matrix with per-layer resource oracles. Then rerun all regressions, ARM/API17 import audit, sanitizers, repo health, and exact-head hosted CI/CodeQL.

Honda-only evidence stays separate and unresolved: actual Honda Display1 admission, warning/safe-area policy, genuine MFi authority and iPhone protocol/security/framing, Honda USB ownership, audio/control equivalence, executable acceptance, and factory restoration. No Honda or vehicle execution occurred.
