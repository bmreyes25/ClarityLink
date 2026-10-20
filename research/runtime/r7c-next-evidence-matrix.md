R7C3 attempt added a test-only socket/JNI route, but runtime verification is pending because this host lacks a JDK. The software rows below remain open; see [R7C3 socket](r7c3-native-socket-runtime.md), [JNI](r7c3-jni-exception-reference-closure.md), [race](r7c3-framework-lifecycle-races.md), [fault matrix](r7c3-final-fault-matrix.md), and [decision](r7c3-r7d-entry-decision.md).

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

R7C5 correction: NDK r23c ARMv7/API17 build/import audit, repository suite, Java/APK build, and host socket/R7C1 sanitizers passed. The API17 emulator did not boot in this attempt. The unresolved R7C rows include deterministic lifecycle races, Android native socket fault and every-cycle coverage, the complete per-cycle resource oracle, and exact-head hosted checks. See [R7C5 entry decision](r7c5-r7d-entry-decision.md).
# R7C6 update (2026-10-08)

Evidence was added for owned API17 AVD creation, Type111 framework Surface
loss, Presentation dismissal, setup/decode cancellation, and socket read/write
shutdown. Open software rows and their exact scope are listed in
`r7c6-final-software-fault-matrix.md`. Historical PR checks remain specific to
`0804bc0...` and do not cover local changes.

## R7C7 closure update — 2026-10-08

| Evidence row | R7C7 result | Classification |
|---|---|---|
| Cumulative API17 Activity lifecycle | 25/25 repeated and passed after cumulative combined race suite | `PASS_EMULATOR` |
| Production Android socket fault matrix | timeout, refusal, peer close, malformed/truncated, zero/oversized declaration, stream/generation isolation, shutdown | `PASS_EMULATOR` |
| Socket-inclusive Android cycles | 100/100 cycles; per-cycle native and FD counters zero | `PASS_EMULATOR` |
| API17 ARMv7 imports | NDK r23c build; zero unknown API17 imports | `PASS_BUILD_AUDIT` |
| Exact PR-head hosted checks | Must run after final push | `PENDING` |
| Honda / real iPhone / MFi / vehicle | Not exercised | `EVIDENCE_REQUIRED` |
