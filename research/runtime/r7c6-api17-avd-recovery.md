# R7C6 API17 AVD recovery

Status: `R7C6_API17_OWNED_AVD_PASS` for the harness smoke.

The pinned isolated SDK is `~/Android/r7c2-sdk`: command-line tools 22.0,
platform-tools/ADB 37.0.1, API17 platform revision 3, API17 default x86 image
revision 7, and Intel emulator 37.2.12 (build 16428233) executed under
Rosetta. The system image is present and intact. The failure was the optional
device catalog: the image-local `devices.xml` needed by `avdmanager --device
'Nexus S'` is absent, so that hardware-profile lookup fails before AVD
creation. Creating a generic AVD without `--device` succeeds and retains the
pinned `system-images;android-17;default;x86` package. No package replacement
or arbitrary AVD was used.

The R7C6 runner passed the API17 / Android 4.2.2 / x86 / Dalvik identity smoke
on unique per-run AVDs. The runner refuses any preexisting ADB target, proves
the launched process, serial, qemu property, API, release, ABI, and console AVD
name, and then performs scoped cleanup. A stale historical AVD was left
untouched. Full runtime closure remains separate from this environment pass.
