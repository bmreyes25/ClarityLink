# R7C next evidence matrix

| Gate | Exact evidence that closes it |
|---|---|
| Android runtime/JNI | Run Surface attach/replacement/loss and native handle, exception, stale-generation, callback-during-shutdown tests on Android API17; compile/import gates are already confirmed |
| Display1 admission | Separately authorized parked-target test: ordinary API17 Presentation on identified external display and observed Surface creation |
| Warning coexistence | With candidate Surface active, observe stock warning/interrupt visibility and blanking response |
| Safe area | Approved physical measurements and warning-boundary validation; no screenshot guesses |
| Process lifecycle | Separately authorized temporary process start/stop; verify no persistent changes and stock startup after stop |
| USB ownership | Lawful transport evidence proving custom receiver may exclusively own the required device/interface |
| iAP2 | Lawful implementation/interface evidence and session lifecycle tests |
| Authentication | Genuine authority producing a complete authenticated session; no jmcs handoff is supported |
| CarPlay framing/security | Real Type110/Type111 protocol and security evidence; synthetic 15-byte envelope is excluded |
| Audio | Target route tests for music, navigation, Siri, calls, volume, mute, and teardown |
| Controls | Observed and approved touch/steering/voice event mapping |
| Stock restoration | Target evidence for reconnect, warnings, stock CarPlay, and factory state after temporary shutdown |
| Performance | Target-like API17/ARM simulation budgets first; target measurements before performance claims |

## R7C2 software closure still required

API17 Dalvik has now executed the real JNI entrypoints, Java DisplayManager/Presentation/Surface path, ANativeWindow sink, actual H.264 Type110/Type111 output, selected Java adapters, and 100 resource-checked cycles on x86. Remaining R7C software evidence: native POSIX `AndroidSocketAdapter` execution through Android JNI (the runtime test is Java loopback), injected pending-exception/reference-failure cases, and deterministic Android Surface/stop/audio callback races plus the remaining fault matrix. Close these rows under [`R7D entry gate`](r7c-r7d-entry-gate.md) before starting R7D. None of these offline gates promotes the Honda-only rows above.
