# R7C build and dependency provenance

| Input/output | Version / digest | Evidence |
|---|---|---|
| Starting source | R7B merge `087f17fb9268f623eabd520c3542b00db0d512b9` | local Git / merged PR #16 |
| Android NDK | r23c `23.2.8568313` | pinned by build script and installed NDK `source.properties` |
| Native target | `armv7a-linux-androideabi17`, `armeabi-v7a` | NDK wrapper build output; ELF32 ARM EABI5 |
| FFmpeg | 6.1.6 | R7B pinned upstream release; archive SHA-256 checked by R7C build script |
| Android Java API | SDK platform 17 / Android 4.2.2 | official platform archive `android-17_r03.zip`; published repository SHA-1 `dbe14101c06e6cdb34e300393e64e64f8c92168a` verified |
| `android.jar` used | SHA-256 `2bf921bd5efce9e4b2966a394d8b9b332e548fa30df7a158e029c7fa823dd799` | extracted from checksum-verified platform archive |
| Java compiler/runtime | OpenJDK 17.0.20.1 | local `javac`; source/target 1.7 against API17 bootclasspath |
| Native library | `libclaritylink_android.so`, SHA-256 `dd4d900e838f56a2973e4209987ee8072e594fdfe3a57d73b184a52902e61e0e` | local ignored build output |
| API imports | 131 imports, 0 unknown | API17 `libandroid`, libc, libm, libdl stubs, `tools/audit_r7c_api17_symbols.py` |
| Java library | `claritylink-android-api17.jar`, SHA-256 `3f3cb23f9ad7fbf2d3e7954d08e665d41b80f9d3eaf6fcf4387559cf3ff2cada` | local ignored output of `tools/compile_android_api17_java.sh` |

Local SDK archive, NDK, Java installation, generated classes, static FFmpeg build, and shared libraries are not tracked. This confirms compilation and import availability only; it does not confirm Android runtime execution or Honda behavior.

## R7C1 rebuild

R7C1 source rebuild, API17 / armeabi-v7a, same NDK and API17 stub set:

| Input/output | Version / digest | Evidence |
|---|---|---|
| R7C1 starting source | `25bf1436f71587e9984940b88d7766a9fa2f44fb` | verified local branch head before edits |
| Native library | `libclaritylink_android.so`, SHA-256 `6581e900dc392185707d16b00b525be451d9873321201da8e363ad7035169bc7` | local ignored R7C1 build output |
| Java library | `claritylink-android-api17.jar`, SHA-256 `c50a009e36ee53196887963832420f55e8b5277c54c48f00383bc4cace6f6dd9` | local ignored API17 compile output |
| API17 imports | 131 imports, 0 unknown | API17 `libandroid`, libc, libm, libdl stubs; `tools/audit_r7c_api17_symbols.py` |
| ELF | ELF32 ARM, EABI5, `armeabi-v7a` target | NDK r23c API17 cross-build and `llvm-readelf` |

The R7C1 hash records this local pre-push build; it does not assert runtime behavior. Build outputs remain ignored and untracked.
