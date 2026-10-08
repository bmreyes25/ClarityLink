# R7C5 NDK r23c recovery

**Result:** NDK r23c installed and ARMv7 production build/import audit passed.

| Field | Value |
|---|---|
| Package | `ndk;23.2.8568313` (Android NDK r23c) |
| Install path | `/Users/bmreyes24/Android/r7c2-sdk/ndk/23.2.8568313` |
| Installer | Existing Android SDK `sdkmanager`, with the R7C4 Temurin 17 selected only for that command |
| Provenance | Android SDK package repository metadata via `sdkmanager`; package revision verified from `source.properties` |
| Archive checksum | The SDK manager removed its temporary archive after installation; no separate archive checksum was retained |
| Compiler | Android Clang 12.0.9, target `armv7a-linux-androideabi17` |

The NDK was not added to Git. The resulting library was built for `armeabi-v7a`, API 17, and audited against NDK API17 Bionic/libandroid stubs. See [the final ARMv7 build record](r7c5-armv7-final-build.md).
