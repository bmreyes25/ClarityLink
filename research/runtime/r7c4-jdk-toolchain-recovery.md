# R7C4 JDK recovery

The host had no selectable Java runtime (`/usr/libexec/java_home -V` empty; system `java`/`javac` shims reported no runtime). The project API17 compile and isolated test APK build require a Java compiler/runtime; Java source compatibility is set to 7, and the Android build-tools are pinned to 35.0.0. A user-local, project-invoked JDK was restored without changing shell startup files or using sudo.

| Field | Value |
|---|---|
| Distribution | Eclipse Temurin, HotSpot JDK |
| Version | 17.0.20.1+1 |
| Architecture | macOS AArch64 |
| Location | `/Users/bmreyes24/.local/toolchains/temurin-17.0.20.1+1-aarch64/jdk-17.0.20.1+1/Contents/Home` |
| Source | [Adoptium version API](https://api.adoptium.net/v3/assets/version/17.0.20.1%2B1?architecture=aarch64&heap_size=normal&image_type=jdk&jvm_impl=hotspot&os=mac&vendor=eclipse) |
| Archive SHA-256 | `196d13ba5f10414bef7f6a05a9b3f00edacb18ebacef2b99485db9e2ee18f0e8` |
| Scope | `JAVA_HOME`/`PATH` set only in build process |

Verification: Java 17 compiler/runtime selected; API17 Java/test APK build succeeded. The API17 emulator uses the preserved Android 4.2.2/API17 x86 image, Dalvik, and the repository's isolated runner. No system-wide JDK selection or tracked dependency change was made.
