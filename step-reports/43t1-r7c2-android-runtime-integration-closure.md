# 43T1-R7C2 — Android API17 runtime integration closure

## Scope and result

Continued PR #17, `architecture/r7c-honda-target-adapters`, from exact R7C2 starting candidate `9ee07dac2b6eda842567b8dbdb3a36cdd7336e54`. Offline-only work. No Honda, vehicle, physical Android device, live CarPlay, CAN, framebuffer, or `/dev/i2c-2` action occurred.

**Decision: `R7C_INTEGRATION_PARTIAL`.** R7C2 closes the actual API17 Dalvik/JNI/Surface integration gap on an isolated x86 emulator and proves 100 integrated receiver cycles. R7C remains incomplete because the native Android POSIX socket adapter was compiled but its runtime path was not called, JNI exception/reference failure injection is not comprehensive, and deterministic Android framework callback/stop races plus parts of the software fault matrix remain open. **R7D entry gate remains CLOSED.**

## Runtime and artifacts

- API17 / Android 4.2.2 / Dalvik; emulator guest x86; evidence `ANDROID_API17_DALVIK_RUNTIME_CONFIRMED_X86` only.
- Pinned emulator 37.2.12 build 16428233 (Intel macOS binary under Rosetta), API17 platform rev 3, `android-17;default;x86` image rev 7, build tools 35.0.0, ADB 37.0.1.
- Isolated SDK at `~/Android/r7c2-sdk`; no SDK, AVD, APK, signing key or build output tracked. Test APK is API17/v1-signature and was installed only into the uniquely created ephemeral AVD after exact serial checks.
- The ARM-host emulator rejected the x86 guest; switching to the matching pinned Intel emulator under Rosetta resolved the host/guest architecture error. This is tool setup only. Runtime evidence remains x86.
- Production ABI rebuilt separately: API17 `armeabi-v7a`, ELF32 ARM EABI5; import/symbol audit remains clean. ARM runtime was not run.
- AOSP API17 overlay display created a synthetic second display at 800×480/160. The setting was cleared and the ephemeral AVD deleted on exit.

## Actual Android path exercised

The test application executed production Java Display0 hosting, `DisplayManager` discovery, the API17 `Presentation` candidate and `SurfaceHolder` callbacks, JNI entrypoints, `ANativeWindow_fromSurface`/geometry/lock/bounded RGBA copy/unlock-and-post, the R7B receiver, and actual FFmpeg H.264 decode for Type110 and Type111 to separate Android Surfaces. Runtime observed two valid displays (0: 480×800, overlay 1: 800×480). Presentation states were observed separately through Surface creation. These are synthetic API17 observations, not Honda evidence.

Selected Java adapters also executed: AudioTrack open/write/pause/resume/flush/close (when available), input allowlist and generation checks, USB manager empty-device enumeration, Java loopback socket, process lifecycle, and fail-closed production iAP2/authentication/CarPlay-media defaults. LAB authentication and synthetic test framing required an explicit test flag; production authentication rejection was asserted before each LAB session.

The harness ran **100/100** actual Dalvik receiver cycles. Every cycle asserted stale-handle rejection and zero test-build native ownership counters after disconnect. The counter snapshot distinguishes actual stream objects from listeners (an ECC review correction), surfaces, JNI globals/workers, decoders and display ownership. Type111 surface invalidation remained stream-local and Type110 continued. Type110 surface invalidation closed the entire session. PSS was sampled at baseline, every ten cycles, and after GC; the retained final logcat window captured cycle 50–100 and post-GC observations, which fluctuated without clear monotonic growth. The logcat ring buffer did not preserve baseline through cycle 30; per-cycle native-owner checks remain complete.

## ECC review: findings, risks, fixes, verification

| Finding | Risk | Fix / verification |
|---|---|---|
| Emulator guest/host architecture mismatch | Mislabeling runtime proof or installing on unintended ADB target | Pinned Intel x86 emulator under Rosetta; exact single serial gate before install/run; successful Dalvik log identifies x86. |
| Arbitrary/recycled handles | Native UAF or ABA | Monotonic opaque handle IDs, validated generation/stream; actual invalid/stale calls plus host concurrent table tests. |
| Surface reference ownership | Premature ANativeWindow release or leak | Temporary JNI conversion ref released; sink owns explicit acquired ref; post path exercised; zero counters each cycle. |
| Lock/reentrancy during teardown | Deadlock/use-after-release | Handle-table work occurs outside registry lock; sink serializes native operations; no native-to-Java worker callback path exists. |
| JNI exception state | Lost Java error or C++ exception escaping ABI | Native exceptions translated; pending exception checked/preserved by implementation. Null Surface rejection tested; exhaustive pending-exception/class-lookup injections remain incomplete. |
| Display enumeration mistaken for safe admission | Type111 on wrong/unsafe target | Distinct candidate states and test-only layout; fail closed outside explicit LAB. Honda warning/safe-area remains unknown. |
| Synthetic authentication/framing reaches production | Unauthorized session or false protocol claim | Production auth and CarPlay media defaults rejected in runtime; synthetic path requires explicit LAB argument. |
| Stream diagnostic count used listener count as a proxy | Misleading resource evidence if future streams lack a listener | ECC review identified and fixed the instrumentation: `ResourceCounts` now reports actual primary/secondary stream object count separately; rebuilt x86/ARM artifacts and reran the 100-cycle Dalvik harness with every counter zero after each cycle. |
| Debuggable test APK | CodeQL flags a debuggable application as a high-severity alert | Removed `android:debuggable`; runner now polls filtered logcat instead of using `run-as`. APK rebuilt and reran in the owned AVD; CodeQL rerun is required on the fix commit. |
| Claims exceed exercised socket/USB paths | False all-adapter closure | Report distinguishes Java loopback from native POSIX Android runtime; UsbManager no-device is real, device permission callbacks were not. |

No blocking memory-safety finding was observed in exercised paths. Software closure remains partial on the rows above.

## Verification

- R7A Python integration and repository suite: passed; full suite reported 902 passed, 14 skipped, plus JavaScript smoke checks.
- R7B native integration/100 cycles: passed.
- R7C policy/process and Java API17 compilation: passed.
- R7C1 integration/surface/handle host tests: passed.
- R7C2 Android API17 Dalvik runtime: `RESULT=PASS`, 100 cycles.
- Host ASan/UBSan and TSan: R7B native, R7C1 integrated adapter, and R7C socket loopback tests passed. Android runtime was not sanitizer-instrumented.
- API17 ARMv7 production library rebuilt; ELF32 ARM EABI5/import audit passed with zero unknown API imports (artifact SHA-256 `00ebf5a3385817949e2d7cfac7eef89e9759a40ee9f0310dbaeb06fa4764fa89`).
- Full repository suite: 902 passed, 14 skipped; repo health: 698 Markdown files, 144 indexed, no curated broken links or forbidden tracked extensions; Java API17 policy/process tests pass; R7B and R7C1 host regression plus ASan/UBSan/TSan pass; socket ASan/UBSan/TSan pass; `git diff --check` pass.
- Exact final HEAD Offline CI and CodeQL are pending push and must be reported only after completion.

## Remaining software work

1. Exercise native `AndroidSocketAdapter` from actual Android/Bionic runtime, including bounded partial I/O and teardown.
2. Add real-VM pending Java exception and lookup/reference failure injections through JNI.
3. Add deterministic barrier-driven framework Surface callback, Presentation dismissal, and process-stop races; complete the software fault matrix.

Honda-only evidence remains separately blocked: genuine MFi, real iPhone `/info` and SETUP, real Type110/111 security/framing, Honda executable, Display0/Display1 admission, safe area/warnings, USB ownership, audio/control equivalence, and factory restoration.

See [runtime baseline](../research/runtime/r7c2-android-runtime-baseline.md), [fault matrix](../research/runtime/r7c2-android-fault-matrix.md), and [R7D entry gate](../research/runtime/r7c-r7d-entry-gate.md).
