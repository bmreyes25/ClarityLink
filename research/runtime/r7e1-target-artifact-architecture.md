# R7E1 diagnostic artifact architecture

**Decision: split artifacts.** Test A uses a tiny native CLI so its intended future check need not install an Android package or initialize the framework. Tests B–D require Android `DisplayManager`, `Presentation`, and a `Surface`, so they use a separate API17 APK. This minimizes Test A capability and mutation scope.

## Test A native artifact

`claritylink-target-diag` is a standalone C executable with `--help`, `--version`, `--status`, and `--self-test`; no arguments show identity and usage then exit. Self-test uses one bounded 64-byte allocation and monotonic-clock reads, then frees it and reports zero resources. Unsupported/extra arguments exit 2. It has no display, network, receiver, USB/iAP2, MFi, CarPlay, persistence, process-spawn, or device-node functionality. It links no production receiver code.

## Tests B–D APK

`claritylink-r7e1-display-diagnostic.apk` reuses production R7C `DisplayDiscovery`, `DisplayPolicy`, and `SecondaryDisplayHost`. Launch is status-only. Enumeration is explicit. Presentation and one-frame modes additionally require an emulator identity gate and an explicit offline-test acknowledgement; the controlled generated geometric frame is 800×480 RGBA PNG. This APK is for isolated emulator evidence only and remains unauthorized for Honda installation.

The split is technically necessary because the native executable cannot call Android framework display APIs without app/runtime context. No Honda compatibility or display-safety conclusion follows from emulator tests.
