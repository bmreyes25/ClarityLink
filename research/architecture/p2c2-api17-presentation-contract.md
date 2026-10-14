# P2-C2 — Android API17 Presentation admission contract

**Scope:** Android 4.2.2/API17 framework source and one isolated x86 API17 emulator. This establishes generic Android behavior only. It does not establish admission, stacking, warning precedence, or an approved safe area on the Honda. The [P2-C1 ownership map](p2c1-display1-ownership.md) remains the Honda-specific baseline. No Honda or iPhone operation occurred.

## Public app route

1. An Android application obtains `DisplayManager` from its `Context`, enumerates `DISPLAY_CATEGORY_PRESENTATION`, and selects a valid, non-default `Display`. API17 uses display *type* for this category; a later `FLAG_PRESENTATION` rule is inapplicable. `getDisplay(id)` returns `null` for an invalid or removed ID. [AOSP API17 DisplayManager](https://android.googlesource.com/platform/frameworks/base/+/android-4.2.2_r1/core/java/android/hardware/display/DisplayManager.java), [Display](https://android.googlesource.com/platform/frameworks/base/+/android-4.2.2_r1/core/java/android/view/Display.java).
2. `Presentation` builds a display-specific `Context`, obtains that context's `WindowManager`, and adds its dialog window to the selected display. The window/session token belongs to the admitted application window; a raw display ID or native `Surface` is not a substitute. `SurfaceView` then supplies a `Surface` after window admission. [AOSP API17 Presentation](https://android.googlesource.com/platform/frameworks/base/+/android-4.2.2_r1/core/java/android/app/Presentation.java), [existing ClarityLink host](../../android/src/main/java/org/claritylink/android/SecondaryDisplayHost.java).
3. The generic public Presentation route uses an Activity/application context. The project-owned host already handles surface creation/destruction, display removal, and close. The new probe exercises it without altering production code. A separately launched temporary native process with **no installed APK** has no demonstrated public API17 app context, window token, or admitted app identity for this route. That is a block for this public implementation under the current no-APK constraint, not a claim that every possible vendor IPC is impossible.
4. A type-2006 `TYPE_SYSTEM_OVERLAY` has a different admission rule. API17 policy requires `SYSTEM_ALERT_WINDOW`; API17 may surface denial as a `BadTokenException` containing `permission denied for this window type`. This is an explicit permission-failure case, not proof that a normal Presentation is denied. [AOSP API17 PhoneWindowManager](https://android.googlesource.com/platform/frameworks/base/+/android-4.2.2_r1/policy/src/com/android/internal/policy/impl/PhoneWindowManager.java), [ViewRootImpl](https://android.googlesource.com/platform/frameworks/base/+/android-4.2.2_r1/core/java/android/view/ViewRootImpl.java).

## Lifetime and safety contract

An app must check display identity/validity before opening; close on display removal and on its own destruction; release the current `Surface` before reusing a host; and withdraw on any admission or geometry failure. The framework reclaims a dead app's window, but a production design must still define lifecycle and warning behavior. P2-C1's Honda owner has three full-frame type-2006 roots on logical Display 1; this emulator has no such Honda roots. Neither app-window admission nor the emulator's process-death cleanup proves Honda z-order, warning priority, physical viewport, or safe sharing.

## Isolated emulator probe

The [test-only Activity](../../android/p2c2-probe/java/org/claritylink/android/P2C2AdmissionProbeActivity.java) reuses `DisplayDiscovery`, `DisplayPolicy`, and `SecondaryDisplayHost`. Its [manifest](../../android/p2c2-probe/AndroidManifest.xml) targets API17 and requests no overlay permission. The [builder](../../tools/build_p2c2_probe.sh) uses the API17 platform jar. The [runner](../../tools/run_p2c2_emulator.sh) starts a dedicated ADB server restricted to a nonexistent USB serial, verifies an initially empty inventory, owns one named x86 API17 emulator, validates its identity, and addresses every emulator command by exact serial through that isolated server. It installs the test APK on that emulator only. Private logs and the APK remain in ignored `build/p2c2/`.

| Case | Required observation |
|---|---|
| Enumeration and invalid ID | One synthetic secondary presentation display; invalid ID rejected. |
| Permission denial | Type-2006 window refused without overlay permission; exception identifies window-type permission. |
| Presentation and Surface | Three create/close cycles and a fourth active Surface; balanced callbacks after close. |
| Display removal | Synthetic display disappears; host closes and all four Surfaces are destroyed. |
| Process death | With a new active Presentation, emulator `force-stop` removes app process and WindowManager root. |
| Repeated lifecycle | No duplicate active Surface and no leaked Surface across cycles. |

Run `tools/build_p2c2_probe.sh` then `tools/run_p2c2_emulator.sh` from this checkout. The emulator test intentionally uses a synthetic 800×480 overlay only; that size is a test fixture, not an approved Honda content area. The runner reports `API17_EMULATOR_PASS` only after all cases complete. Its local evidence is `build/p2c2/first-run.log`, `second-run.log`, and `emulator.log` (ignored; not PR artifacts).

On 2026-10-12 the end-to-end isolated run returned `API17_EMULATOR_PASS`: invalid ID, explicit window-type permission denial, three create/close cycles, fourth Surface removal, and process/window reclamation all passed. The test APK SHA256 was `40aa30cf9cc5e33063338b7abdb874b89a43899cdd5af3edac2f918901c9b455`; the private first and second log SHA256 values were `030dbeb2438c4798bf27bd32c2c28ac07b61d28adc8b1c527702e1478f684606` and `738224ed651ad5d36a26893021001b30d4b73bc24fd56ef7a27c2f62022768f5`. A prior exploratory run exposed API17's `BadTokenException` permission-denial form and an API17 `settings put` empty-value quoting error; both were corrected before this complete automated pass. No result from the exploratory runs is used as a pass claim.

**Manual ECC-guided review:** The probe is test-only, signed with a local debug key, and has no Honda/phone endpoint. The runner uses an isolated ADB server, a deliberately nonexistent USB allowance, one verified emulator serial, and bounded waits. It neither grants an overlay permission nor turns an emulator success into a Honda admission claim. The primary remaining safety gap is Honda-specific caller admission, window priority and physical protected geometry. No independent ECC reviewer was invoked for this chunk.

## Admission decision

The generic API17 Presentation mechanism is usable by an admitted app on the isolated emulator. **Honda admission remains unknown.** Under the current no-APK constraint, this public app route is unavailable to ClarityLink's temporary native process. A vendor-provided external window or Surface handoff would need a separately proven caller contract, token/Surface ownership, safe region, priority, lifecycle, and cleanup. P2-C3 reviews those alternatives; emulator success does not authorize an APK install or a Honda display operation.
