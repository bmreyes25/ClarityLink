# P2-C1 — Display 1 ownership and external seam map

**Scope:** offline static/decompiled Honda evidence, saved read-only display observations and version-matched Android 4.2.2/API17 source. Starting HEAD `7989f7c11e7dd87231a85a017ee06ba7c26a5594` is the [P1 receiver-ingress closeout](../../step-reports/p1-receiver-ingress-feasibility-closeout.md). P1's stock-session NO-GO remains in force: a Display 1 pixel path alone cannot supply authentic iPhone content. No Honda display action, APK installation, ADB command, framebuffer access or new phone session occurred.

## Ownership and composition

```text
Honda Navigation / CarPlay status / phone / audio / interrupt state
      → ExternalDisplayOutService (UID 10056 in saved packages.xml)
      → InterfaceWindow bottom, main, interrupt View roots
      → display-context WindowManager windows (type 2006, full 800×480)
      → WindowManager / SurfaceFlinger layer stack 1
      → HDMI logical Display 1 → downstream cluster composition (exact transform unknown)
```

The preserved decompiled `ExternalDisplayOutService.createWindow()` uses `DisplayManager.getDisplays()`, selects the final display, calls `Context.createDisplayContext`, and takes that context's `WindowManager` (lines 988–1024). `InterfaceWindow.createInitScreen()` adds three roots (lines 101–138); `ViewControl.createWindowParameter()` makes each `MATCH_PARENT`, type 2006 (lines 543–554). Root removal occurs in `InterfaceWindow` lines 48–63. The saved package state places the render host at UID 10056 and the separate ExternalDisplay AP process at UID 10055; their permissions cannot be inferred from one another. Decompiled files are private sibling-checkout evidence, not original APK bytes: the exact reviewed `.java` and manifest hashes are in [the seams matrix](p2c1-display-seams.json). [R4C owner audit](../runtime/43t1-r4c-honda-display1-ownership-audit.md), [host flow](../display/externaldisplay-host-flow.md), [package grants](../runtime/43t1-r4d-package-grants-permission-resolution.md).

Saved `dumpsys display`/SurfaceFlinger/WindowManager observations identify logical Display 1 as HDMI, 800×480, layer stack 1, with full-frame externaldisplay-owned windows. `fb1` aligns with Tegra `tegradc.1` by index and mode, but that does not prove a safe raw pixel interface or exact framebuffer format. The paired physical photo contains indicators absent from the Display 1 capture. The downstream crop, physical navigation viewport, warning priority and safe region are **unknown**. [Diagnostics](../cluster-display-diagnostics.md), [safe-area evidence](../navigation-safe-area.md), [warning audit](../runtime/43t1-r4d-warning-zorder-static-evidence.md).

## Interface classification

| Candidate boundary | Classification | What is established; missing proof |
|---|---|---|
| Public API17 `DisplayManager.getDisplays()` | `SUPPORTED` **for enumeration only** | Generic Android API and Honda service use are visible. Enumeration is not ordinary-app window admission. |
| Ordinary app `Presentation` targeting HDMI Display 1 | `UNKNOWN` | Android API17 creates a display-bound dialog, but no preserved normal-app Honda window success, UID admission, z-order, or warning-safe placement. Best independent-window research lead, not a GO. |
| Separate display-context `WindowManager` app window | `UNKNOWN` | API17 mechanism exists; exact Honda window policy and overlap with three full-screen type-2006 roots are unresolved. A competing system overlay is not a safe substitute. |
| `ExternalDisplayOutService` `InterfaceWindow.addView`/root getters | `PROCESS_LOCAL` | Real Honda View composition, but static methods act in the host process. Exported service `onBind()` returns `null` (line 740). No arbitrary external View/Surface/frame ABI. |
| `ExternalDisplayApService` Binder | `UNKNOWN` as a new caller; **control/status only** | Exported control transactions exist, with no reviewed arbitrary pixel/Surface/FD parameter. Effective method permissions/additional-client admission unknown. |
| Navigation/TBT services | `UNKNOWN` as a new caller; **semantic content only** | Route and guidance objects are Honda-native unless provenance shows otherwise. No external window or pixel ownership contract. Calls could change stock Navigation. |
| `disp_com_meter` / cluster control | `UNKNOWN` | Preserved strings/scripts show command or meter messaging, not a supported content surface, safe viewport, or caller ABI. |
| Direct SurfaceFlinger/layer transaction | `PRIVILEGED` | SurfaceFlinger is the compositor, not an application content handoff. Direct layer ownership/permission and safety contract for ClarityLink are absent. |
| Direct `/dev/graphics/fb1` access | `PROHIBITED` | Bypasses Android window priority; format, allocation and physical warning boundary unproved. No framebuffer takeover is authorized. |
| HondaHack/Xposed View insertion | `PROHIBITED` | A historical in-process composition precedent, not an external API; injection violates the stated boundary. |
| ClarityLink JNI `Surface`/Display1 adapter | `PROCESS_LOCAL` until an admitted window exists | Useful offline rendering code, but an owned `Surface` cannot create permission or stock warning priority by itself. |

The [machine-readable matrix](p2c1-display-seams.json) records owner, caller identity, permissions, surface/layer, lifetime, evidence and decisive missing experiment for each entry. `SUPPORTED` in the first row deliberately means *discovery of display objects*, not a supported safe Display 1 renderer. No reviewed candidate is classified `SUPPORTED` for a separately controlled, warning-safe content window on this Honda.

**No-APK boundary:** `Presentation`, `DisplayManager` and an app-owned `WindowManager` route require a running Android app/context and an admitted window token. The public API17 route is a possible *future app design*, not a callable interface already available to an uninstalled temporary native ClarityLink process. This milestone permits no APK installation. The project JNI/Surface adapter likewise needs an admitted app window first. A Binder or native service would need its own separately proved caller contract; none of the reviewed control/status interfaces grants this window.

## API17 and safety distinctions

Android 4.2.2's [`DisplayManager`](https://android.googlesource.com/platform/frameworks/base/+/android-4.2.2_r1/core/java/android/hardware/display/DisplayManager.java) selects presentation displays by display **type**, including HDMI; the later `Display.FLAG_PRESENTATION` rule must not be projected backward. [`Presentation`](https://android.googlesource.com/platform/frameworks/base/+/android-4.2.2_r1/core/java/android/app/Presentation.java) uses a display context and cancels on display removal. In [API17 `PhoneWindowManager`](https://android.googlesource.com/platform/frameworks/base/+/android-4.2.2_r1/policy/src/com/android/internal/policy/impl/PhoneWindowManager.java), type-2006 system overlays require `SYSTEM_ALERT_WINDOW`, while other system window types can require signature `INTERNAL_SYSTEM_WINDOW`. The saved Honda host requests both; its *effective grants* and an ordinary package's admission remain unresolved. No public API17 targeted Activity launch or API19 virtual-display capability solves this existing physical HDMI path. [R4C API17 audit](../runtime/43t1-r4c-api17-external-display-static-review.md), [R4D policy audit](../runtime/43t1-r4d-framework-window-policy-audit.md).

`ExternalDisplayApService` is Binder IPC, but its methods carry LVDS/channel/meter/interrupt status and control rather than `View`, `Surface`, `Bitmap`, frame bytes or a display window token. `ExternalDisplayOutService` is the actual View-root owner and does not return a Binder from `onBind`. The named `Navigation` and `disp_com_meter` paths offer semantic/control signals, not a proven user-space pixel sink. The only observed third-party insertion used HondaHack/Xposed inside Honda's render host. Do not treat that as an allowed separate-process seam. [API surface](../display/externaldisplay-api-surface.md), [ownership audit](../runtime/43t1-r4c-honda-display1-ownership-audit.md).

## Decision and next evidence

**P2-C1 finding:** a stock render owner is identified; an independently controlled, safely admitted Display 1 window is **UNKNOWN**. The narrowest candidate is a normal app's public API17 `Presentation`, but no APK installation or Honda trial is authorized here. First seek a build-matched Honda window/display policy or an existing, provenance-verified normal-app admission record that establishes UID/type/token rules and non-displacement of Honda roots. Separately obtain authoritative warning layer/physical viewport evidence. If these offline sources do not resolve the questions, propose one bounded, separately authorized experiment with explicit rollback and warning safeguards. Do not infer a safe rectangle from the 800×480 logical frame or a physical photo alone. P2-C2 may examine these gates next; it has not started.
