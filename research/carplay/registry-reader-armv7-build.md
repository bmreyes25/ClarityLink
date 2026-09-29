# ARMv7/API 17 registry reader build and audit

Date: 2026-09-29. Offline only. The reader was not run on the Honda, and no ADB or vehicle was used in this milestone.

## Result

| Item | Result |
|---|---|
| NDK | r23c, revision 23.2.8568313 |
| Artifact | `android-ndk-r23c-darwin.dmg`, official Android NDK Unsupported Downloads archive |
| Expected SHA-1 | `da6f63d3eef041e1cceca449461c6d9148e879b7` |
| Actual SHA-1 | `da6f63d3eef041e1cceca449461c6d9148e879b7` |
| Match | YES |
| NDK already installed before this work | NO |
| Installed/copied into SDK | NO; mounted verified DMG, toolchain remains outside repository |
| Host | Apple Silicon, `arm64` |
| NDK compiler tools | Universal arm64/x86_64 Mach-O; invoked natively as arm64 |
| Rosetta | Available; not required |
| Target | `armeabi-v7a`, `armv7a-linux-androideabi17` |
| API | 17 |
| Language/runtime | C; Bionic libc only, no C++, JNI, Java, or framework APIs |
| Source revision | `81c273a` plus this milestone's reader/Makefile changes; source SHA-256 below |
| Compiler | Android clang 12.0.9 (NDK build based on r416183c2; build `8481493`) |

The authoritative published checksum is in the [official Android NDK Unsupported Downloads archive](https://github.com/android/ndk/wiki/Unsupported-Downloads), r23c row. The archive lists the DMG size as 1,542,594,243 bytes and this SHA-1.

## Build

The Makefile target is `research/tools/jmcs_registry_reader/Makefile:armv7`. Reproduction command (with the verified DMG mounted at the same path):

```sh
make test safety
make armv7 NDK_ROOT='/Volumes/Android NDK r23c/AndroidNDK8568313.app/Contents/NDK'
```

Full compiler command:

```sh
"/Volumes/Android NDK r23c/AndroidNDK8568313.app/Contents/NDK/toolchains/llvm/prebuilt/darwin-x86_64/bin/clang" --target=armv7a-linux-androideabi17 --sysroot="/Volumes/Android NDK r23c/AndroidNDK8568313.app/Contents/NDK/toolchains/llvm/prebuilt/darwin-x86_64/sysroot" -O2 -Wall -Wextra -Werror -std=c11 -march=armv7-a -mfloat-abi=softfp -fPIE -pie -Wl,-z,relro,-z,now -o jmcs_registry_reader reader.c
```

No SIMD/NEON option is enabled. `-march=armv7-a` constrains generated code to ARMv7-A. Binary is kept as ignored local build output and is not committed.

## Syscall ABI

Header inspected from the exact verified NDK:

```text
toolchains/llvm/prebuilt/darwin-x86_64/sysroot/usr/include/arm-linux-androideabi/asm/unistd.h
  includes asm/unistd-eabi.h
  __NR_SYSCALL_BASE = 0

toolchains/llvm/prebuilt/darwin-x86_64/sysroot/usr/include/arm-linux-androideabi/asm/unistd-eabi.h
  __NR_process_vm_readv = __NR_SYSCALL_BASE + 376
```

Therefore the ARM EABI number is **376**, verified from the target-specific NDK header, not copied from a generic web table. The Android ARM source includes `<asm/unistd.h>` and compile-time asserts `__NR_process_vm_readv == 376`. It invokes the kernel through Bionic `syscall()`. The syscall ABI is VERIFIED. Whether the Honda/NVIDIA kernel implements it remains UNKNOWN; the known kernel baseline is Linux 3.1.10, and no Honda backport evidence exists. `ENOSYS` is an expected clean unsupported result and never triggers fallback.

## ELF and instruction audit

Audited with NDK `llvm-readelf`, `llvm-objdump`, and macOS `file`:

| Property | Observed |
|---|---|
| File | ELF 32-bit LSB PIE executable |
| ELF class / byte order | ELFCLASS32 / little endian |
| Machine / ABI | ARM / EABI5 |
| Type / flags | ET_DYN PIE / EABI version 5, hard-float flag not set |
| Entry | `0x1aec` |
| Interpreter | `/system/bin/linker` |
| `DT_NEEDED` | `libdl.so`, `libc.so` |
| Relocations/security flags | BIND_NOW, PIE, RELRO; non-executable GNU_STACK |
| ARM attributes | ARMv7 application profile, ARM ISA permitted, Thumb-2 permitted, VFPv3-D16 ABI attribute |
| Disassembly state | ARM state; no Thumb instruction ranges found in `$t` mapping markers |
| NEON/ARMv8 | None enabled or observed |
| Host format | Not Mach-O; executable is Android/Linux ARM ELF |

The VFPv3-D16 attribute is emitted by the ARMv7 Android target configuration; this integer-only reader contains no floating-point work. No ARMv8 or NEON feature flag was requested.

## Dependencies and imported symbols

The forensic firmware copy at `extracted/system-vendor/system/` contains the exact required 32-bit ARM files: `bin/linker`, `lib/libc.so`, and `lib/libdl.so`. All imports below are `@LIBC`, resolve by name in the saved target `libc.so`, and are established in Android/Bionic well before API 17. The saved `libc.so` export table was inspected directly.

| Undefined symbol | Source library | Saved firmware export / API 17 |
|---|---|---|
| `__cxa_atexit` | `libc.so` | YES |
| `__libc_init` | `libc.so` | YES |
| `__errno` | `libc.so` | YES |
| `__sF` | `libc.so` | YES |
| `close` | `libc.so` | YES |
| `fclose` | `libc.so` | YES |
| `fgets` | `libc.so` | YES |
| `fopen` | `libc.so` | YES |
| `fprintf` | `libc.so` | YES |
| `fwrite` | `libc.so` | YES |
| `memcmp` | `libc.so` | YES |
| `open` | `libc.so` | YES |
| `printf` | `libc.so` | YES |
| `read` | `libc.so` | YES |
| `snprintf` | `libc.so` | YES |
| `sscanf` | `libc.so` | YES |
| `strcmp` | `libc.so` | YES |
| `strtol` | `libc.so` | YES |
| `strtoul` | `libc.so` | YES |
| `syscall` | `libc.so` | YES |
| `memcpy` | `libc.so` | YES |
| `memset` | `libc.so` | YES |

`strtoull`, `getline`, time/clock functions, and JSON libraries are not imported. NDK r23c emits `LIBC` symbol-version metadata, while Android linker symbol versioning is documented as API 23+. For this API 17 target, the saved firmware exports the unversioned names and the pre-23 linker uses legacy lookup behavior; this is an offline compatibility audit, not a runtime execution proof.

## Safety and read bounds

`llvm-readelf --dyn-syms`, `strings`, and source review found no target write syscall/API, `ptrace`, `kill`, `tgkill`, `raise`, debuggerd, `PTRACE_POKE*`, code-modifying `mprotect`, injection `dlopen`, or `/proc/%d/mem`. `process_vm_readv` is read-only. Output writes go only to this process's stdout/stderr.

| Bound | Value |
|---|---:|
| `MAX_ENTRIES` | 128 |
| `MAX_ATTEMPTS` | 2 |
| Passes per attempt | 2 |
| Bytes per pass at 128 entries | `8 + 20*128 = 2,568` |
| Maximum target bytes | `2 * 2 * 2,568 = 10,272` |

The matching source constants are unchanged. Synthetic tests pass, including 128/129-entry boundaries, consistency mutation, short read, and `ENOSYS`/permission/PID failures. The ARM ELF has not been executed in an emulator or on the car.

## Reproducibility identifiers

```text
SOURCE COMMIT: milestone commit (recorded in final task result)
SOURCE SHA256 (reader.c): 7ebd3506b5accb518e846cd29e458e7788bfd1a835eede8b05bdbe7f082a7f80
BINARY SHA256: c418c8622e6d2a490f5a53074a0364fdbffcd8ff12ce3c7f061eadf5d442e8ec
NDK: 23.2.8568313
COMPILER: Android clang 12.0.9 (8481493)
```

## Go / no-go

| Gate | Result |
|---|---|
| ARMv7/API17 build | PASS |
| Syscall number/ABI | VERIFIED: ARM EABI 376 from exact NDK header |
| Kernel support | UNKNOWN |
| ELF / ISA audit | PASS |
| Firmware dependency audit | PASS |
| API 17 symbol audit | PASS against saved firmware exports |
| Safety audit | PASS |
| Synthetic tests | PASS |
| Ready for separately authorized vehicle attempt | YES |

The expected first live result may be `ENOSYS`; that is a kernel compatibility result, not a reason to retry through another mechanism. No future vehicle command in the companion reader guide has been run.
