# R7E1 target diagnostic artifact manifest

Build source revision: `5b1d490` (`5b1d490` commit). Exact source commit and reproduction commands are in the build scripts and Git history. Artifacts are build outputs under ignored `build/r7e1/` and are not committed.

| Artifact | Purpose / tests | Format, API, ABI | Size | SHA-256 |
|---|---|---|---:|---|
| `claritylink-target-diag` | Test A temporary executable acceptance only | ELF32 ARM EABI5 PIE, API17, `armeabi-v7a` | 4,836 bytes | `f2e12aafe221ff51e153ccc7c1b71402cf3cf0c3a4f1648fb5963e2e66cffca0` |
| `claritylink-target-diag` (x86 test build) | Isolated API17 emulator runtime only | Android x86 ELF, API17 | 4,836 bytes | Build manifest under ignored output |
| `claritylink-r7e1-display-diagnostic.apk` | Emulator-only B–D diagnostics | APK, min/target SDK 17 | 17,949 bytes | `c92f103b49fae2cfd6aa8863a27448042d282708ffec3f5f5c4000c0e6528f5c` |
| `r7e1-diagnostic-frame.png` | Emulator-only single-frame test asset | 800×480 RGBA8 geometric pattern | 4,510 bytes | `02730d7e4ee85464f9cd0656e7c8cb64a8427d7dbd0044ba4937c5ff8246a320` |

NDK: r23c `23.2.8568313`, API17 wrapper `armv7a-linux-androideabi17-clang`. ARM ELF NEEDED: `libdl.so`, `libc.so`, both API17 standard. Ten unique dynamic imports were compared against API17 NDK stubs; zero unknown. Default/no-argument CLI prints identity/usage and exits 0. Modes: `--help`, `--version`, `--status`, `--self-test`; invalid/unauthorized modes exit 2. No persistent writes, network, display, USB, auth, or receiver behavior. APK has no declared permissions; it has framework display code in a separate package and explicit emulator gating for surface/frame modes. Test/debug signing material and all artifacts remain ignored build outputs.
