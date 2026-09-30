# API 17 ARM runtime availability — Step 40D

## Official image obtained

The official Android system-image repository index `https://dl.google.com/android/repository/sys-img/android/sys-img.xml` listed API 17 `armeabi-v7a-17_r06.zip`, branch `jb-mr1.1-emu-release-arm`, build date 2019-02-21, size 124,437,041 bytes, SHA-1 `a18a3fd0958ec4ef52507f58e414fc5c7dfd59d6`. Downloaded archive SHA-256: `f6953289a7e2bd2fd9a6418afe445a7f3dde4e07dcdbbdfa1b80c9cf5abcef93`; the official repository SHA-1 matched. The system image and extracted files are in `/tmp/clarity-step40d/`, not Git. It is Google's generic API 17 ARM emulator image, not Honda firmware.

The signed Google macOS x86_64 Android Emulator package was also obtained from Google's official repository metadata and its package SHA-1 matched. On this Apple Silicon host, the emulator's QEMU2 backend exits with `CPU Architecture 'arm' is not supported by the QEMU2 emulator`; explicitly selecting the classic engine yields the same unsupported-ARM fatal. The installed QEMU system ARM binary has no `goldfish` machine, which this old image requires. No Android guest boot or test program execution occurred. The emulator binary's main code signature identifies Developer ID Application Google LLC; no downloaded scripts or guest payloads were executed beyond the emulator's help/version startup and failed VM-engine selection.

## Result

`API17 ARM RUNTIME: NOT READY`. `REAL ARM THUMB EXECUTION: NOT AVAILABLE`. No ARM `mmap`, `mprotect`, `cacheflush`, signal, futex, `/proc/self/task`, synthetic patch, veneer, or thread-rendezvous test was run. The repository's host models and Python tests are not an ARM runtime substitute. The generic official image is preserved as a reproducible input, but the available host emulator cannot execute its ARM guest. This attempt is closed; do not repeatedly retry the same unsupported emulator.

Next environment work, if needed, should use a disposable Linux environment with a documented compatible Goldfish-capable legacy emulator or build/run a minimal ARMv7/API17 userspace under an explicitly validated machine model. Do not represent that environment as Honda kernel execution.
