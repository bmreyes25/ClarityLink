# CL-IMP-03 — Independent Android API 17 application adapter

**Status:** implemented and verified on an isolated Android 4.2.2/API 17 x86 emulator. The lab app renders synthetic pixels only. Production Honda integration remains disabled.

## Application and admission boundary

- `ClarityLinkDisplayActivity` is a standalone API 17 app entry point that starts status-only. It does not enumerate or select a display until the explicit emulator lab mode and confirmation token are supplied.
- The adapter accepts only an emulator fingerprint/hardware and a unique, valid, non-primary 800×480 display. It uses the existing `DisplayDiscovery`, `DisplayPolicy`, and `SecondaryDisplayHost` APIs.
- `SecondaryDisplayHost.HostedContentListener` supplies the Presentation-owned `FrameLayout` created with the selected display context. The app attaches the CL-IMP-02 `Display1OutputBackend` and `ClarityLinkContentView` into that root.
- The emulator lab manifest declares no permissions. The separate future candidate APK has both the application and activity disabled and is never installed by the emulator runner.
- `PRODUCTION_HONDA_INTEGRATION_ENABLED` is fixed false. The app contains no Honda root lookup, hook, stock-process, USB, iAP2, authentication, Type110, or Type111 operation.

## Lifecycle and ownership

- Activity pause/destroy closes the renderer and Presentation. Display removal is reported by `SecondaryDisplayHost`, which releases the app-owned renderer View and Presentation.
- The Activity records the Presentation `Surface` as borrowed from its `SurfaceHolder`. It clears its reference on loss/close and never calls `Surface.release()`; the Presentation/SurfaceHolder owns that resource.
- Session generations are process-local. Saved state never restores lab admission. After an app crash, the system error dialog is explicitly dismissed in the emulator, the process/window are checked gone, and a fresh launch remains status-only.
- API 17 requires no runtime permission flow here. The app requests no permission, and Presentation admission errors fail closed with operation/type diagnostics.

## Verification

- `tools/build_cl_imp_03_apks.sh` produced the API 17 lab APK (`SHA-256 c609052d9676c33a781626cd688aa0b5565fa9fc47e0c1cb5ab19c46ab666ce2`) and disabled candidate APK (`SHA-256 0bda5a85baefeaad09de89cc739c25621cf0af0d2ca1bb006717eee3cb96e459`). The candidate artifact was not installed.
- `tools/run_cl_imp_03_emulator.sh` installs only the lab APK on the isolated API 17 x86 emulator. It observes display discovery, Presentation admission, a borrowed Presentation Surface, a synthetic frame drawn by the hosted View's Android `Canvas.onDraw`, display-removal teardown, the deliberate emulator-only crash, process/window reclamation after force-stop dismissal of the Android 4.2.2 error dialog, status-only relaunch, and package uninstall. The Canvas draw acknowledgment does not prove compositor presentation or physical display scanout.
- Focused contract tests: 6 passed. API 17 Java policy/lifecycle/frame tests passed. Full offline regression: 1,373 passed, 14 skipped; the self-locator smoke suite (3 checks) and simulator checks passed. Repository health passed.

These results establish public API behavior on an emulator only. `SYNTHETIC_FRAME_DRAWN_ON_PRESENTATION_CANVAS` means `Canvas.drawBitmap` returned from the hosted View's `onDraw`; it does not mean display scanout or `FIRST_FRAME_PRESENTED`. The candidate artifact is disabled and has not been installed on a vehicle. Honda Display 1 availability, production permission policy, warning authority, physical safe area, Type111 negotiation/security, and authentic iPhone content remain unproven.
