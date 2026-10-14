# Display 1 observation plan — V5 through V7

## What evidence says today

P2-C5's existing package is specifically a logical display-service inventory. Collector SHA-256 `39278b643a58b7f32bf624a6fa04ea90da26f7dedbb91518ed05c24a4576383b`; manifest SHA-256 `e136920f4eb61afbacebc998f2efce72c006fca1fd963ff349049d047daed8a4`. Its exact ordered future commands are:

1. `adb -s <EXACT_SERIAL> get-state`
2. `adb -s <EXACT_SERIAL> shell id`
3. `adb -s <EXACT_SERIAL> shell getprop ro.build.version.sdk`
4. `adb -s <EXACT_SERIAL> shell dumpsys display`

The collector checks `uid=2000(shell)`, API level 17, expected target state, nonempty output, and private evidence destination. Each command has a 12-second timeout, with no retries or fallbacks. It does not change settings, create a display, install an APK, or render. Its existing hash-bound mechanism is a package identity gate plus explicit authorization reference and fresh operator conditions; it is not itself an authorization. A new single-use authorization is required.

Because current process/relaunch state is unresolved and ADB ownership must remain exclusive, this plan **defers V5** until a separate review accepts the shared-ADB and target-state risk. Never start it concurrently with Phase S, V2, Phase C, Test A, or another collector.

## V5 — logical display inventory

Potentially answers what the Honda framework's display service reports: IDs, logical dimensions, density/configuration and display type/flags if present in the returned dump. First verify that exact Honda build exposes the expected format and that shell identity is sufficient. Empty/unparseable or permission-limited output is inconclusive. Success is only `DISPLAY_ENUMERATION_RAW_ONLY`: it does not prove a `Presentation` context, window token/admission, Surface lifecycle, physical viewport, safe navigation region, warning priority, or visible rendering.

## V6 — stock composition and warning boundary

No command package is prepared. Existing saved evidence reports logical Display 1 as 800×480 with full-frame logical SurfaceFlinger rectangles; the linked paired physical image is not present in this checkout, and even a photo alone cannot calibrate transform or establish layer precedence. The safe-area example values are explicitly synthetic. Existing static reports show the stock renderer/ownership boundary but do not establish current runtime window roots or warning order.

Do not run a broad `dumpsys`, `dumpsys window`, SurfaceFlinger dump, screenshot, warning trigger, or overlay experiment by inference. An offline Android 4.2.2/vendor-build review must first identify a single bounded read-only source whose output changes a design decision, expected grammar, permission, privacy impact, timeout and stop rule. If it cannot reveal a physical safe boundary or warning precedence without manipulation, report that limitation and keep V6 blocked. Any later rendering experiment is outside this plan and requires new safety review.

## V7 — window admission

Not ready: `WINDOW_ADMISSION_TEST_NOT_READY`. AOSP API17 `Presentation` shows an API shape, not Honda permission/admission. A normal app context or temporary APK would change the existing no-APK constraint; that constraint must be explicitly changed by the user before preparing a runnable visual test. Further gates: actual UID/signature/permission result; display token/admission; Honda root coexistence and z-order; lifecycle/teardown on display/process death; calibrated physical safe geometry; stock warning preemption; bounded duration; independently reviewed rollback and uninstall; and a non-critical test surface selected by evidence. Do not create an exploratory window or show a test pattern over unknown vehicle-critical regions.

## Physical coordinates

The 800×480 logical canvas is not a physical cluster measurement. The saved pictures can document visible content and apparent extents only. A physical transform requires calibrated measurements with method, uncertainty, camera/viewpoint and device/display orientation. Warning-safe regions and z-order require authoritative OEM evidence or a separately designed safe observation; neither can be inferred by hiding, overlaying, or deliberately triggering a vehicle warning. Keep physical safe-area status `UNKNOWN`.
