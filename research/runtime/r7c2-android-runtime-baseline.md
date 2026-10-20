# R7C2 Android runtime baseline

## Result

`R7C2_API17_X86_RUNTIME_AVAILABLE`. Runtime evidence is `ANDROID_API17_DALVIK_RUNTIME_CONFIRMED_X86`; it is not ARM runtime evidence and says nothing about Honda acceptance.

| Component | Pinned/observed value |
|---|---|
| Android platform | API 17, Android 4.2.2, platform revision 3 |
| Runtime | Dalvik (`java.vm.name=Dalvik`) |
| Emulator guest | x86, system image `android-17;default;x86`, revision 7 |
| Emulator | 37.2.12, build 16428233 |
| Host execution | Intel x86_64 emulator under Rosetta on Apple Silicon; ARM-host emulator rejected the x86 guest |
| Build tools | 35.0.0; APK min/target SDK 17, v1 signature |
| ADB | 37.0.1 |
| Native test target | `i686-linux-android17`, built from shared Android JNI source paths |
| Production target | `armv7a-linux-androideabi17`, `armeabi-v7a`; separately rebuilt and audited |

The API17 platform and system image were obtained with the official Android SDK package manager. The Intel emulator archive checksum was SHA-256 `9fdae8c07ac92155aeb175835669ef9b12adf19130f5557792139fb4ebd01256`; the command-line tools archive checksum was `835b62a26162b229b441d1f6d4680383815a270809eb33522c0d480fa5002c4e`. See the [official emulator archive](https://developer.android.com/studio/emulator_archive) and the [API17 AOSP OverlayDisplayAdapter](https://android.googlesource.com/platform/frameworks/base/%2B/e7ae644/services/java/com/android/server/display/OverlayDisplayAdapter.java) used to verify the simulated-display mechanism. The isolated SDK resides outside Git at `~/Android/r7c2-sdk`. No SDK, image, APK, AVD, key, or build artifact is tracked.

The default ARM-host emulator rejected the x86 guest. ECC finding: selecting an emulator by filename alone could silently imply the wrong guest/host pairing. Fix: use the version-pinned Intel emulator under Rosetta, validate the sole exact serial, and label the evidence x86. The first boot took several minutes under software translation; this is a tool/runtime limitation, not Honda performance data.

## Synthetic secondary display

API17 AOSP `OverlayDisplayAdapter` is enabled only inside the ephemeral AVD with `settings put global overlay_display_devices '800x480/160'`. The setting is cleared by the harness before emulator shutdown. The resulting 800×480/160 display is synthetic. It is not a Honda cluster geometry or safe area.

## Build and runtime evidence

`tools/build_r7c_android_api17_x86.sh`, `tools/build_r7c2_test_apk.sh`, and `tools/run_r7c2_emulator.sh` produce and run an isolated test application. The harness reports `RESULT=PASS`, 100 cycles, Dalvik, API 17. With corrected stream diagnostics, test APK SHA-256: `db772a3f0efa9f5be62f7a6ace1dc0f49546ac175095ec777bfb42c68ac83f60`. Runtime library SHA-256: `f220612fb1f83c52f7afd1dececce3834400c22515b3d3a5a3b7a76a23180f88`. Production ARMv7 library SHA-256: `00ebf5a3385817949e2d7cfac7eef89e9759a40ee9f0310dbaeb06fa4764fa89`.

Evidence level: `ANDROID_API17_DALVIK_RUNTIME_CONFIRMED_X86` for the exercised Java/JNI path; `ANDROID_ARMV7_BUILD_CONFIRMED` for the separately built production ABI. This report does not claim `ANDROID_ARMV7_RUNTIME_CONFIRMED` or Honda compatibility.
