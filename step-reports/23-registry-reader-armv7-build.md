# Step 23 — ARMv7/API 17 registry reader build and audit

Date: 2026-09-29
Base: `81c273affcacdfa1ca6f5df02017ade209fcd9e0`
Scope: offline build and audit only.

## Work performed

- Confirmed no NDK r23c existed in the environment or common SDK locations; inspected `ANDROID_NDK_HOME`, `ANDROID_NDK_ROOT`, `ANDROID_HOME`, and `ANDROID_SDK_ROOT`.
- Obtained only the official Android NDK r23c macOS DMG. Published and actual SHA-1 both equal `da6f63d3eef041e1cceca449461c6d9148e879b7`. NDK revision reports `23.2.8568313`.
- The developer Mac is Apple Silicon. NDK clang and audit utilities are universal arm64/x86_64 binaries. They executed natively as arm64. Rosetta was already available but was not needed or installed.
- Built C-only target `armv7a-linux-androideabi17` (`armeabi-v7a`) with NDK clang 12.0.9 and API 17 sysroot. The exact build command is in `research/carplay/registry-reader-armv7-build.md` and the reusable Makefile target is in `research/tools/jmcs_registry_reader/Makefile`.
- Verified the ARM EABI syscall header in the exact NDK: `__NR_SYSCALL_BASE=0`; `__NR_process_vm_readv=__NR_SYSCALL_BASE+376`. Added a compile-time assertion for 376 on Android ARM. The source uses Bionic `syscall()` and fails closed for syscall errors.
- Audited the final ELF, ARM attributes/disassembly, dynamic imports, dynamic dependencies, forensic firmware libraries/linker, forbidden-operation strings/imports, and source read bounds.
- Ran synthetic tests and `git diff --check` (see recorded results below).

## Audit results

| Gate | Result | Evidence |
|---|---|---|
| ARMv7/API 17 build | PASS | ELF32 ARM PIE, EABI5, interpreter `/system/bin/linker` |
| Syscall number/ABI | VERIFIED | NDK r23c ARM EABI header, static assert 376 |
| Kernel support | UNKNOWN | Likely 3.1.10 baseline; no backport evidence; `ENOSYS` stops safely |
| ELF/ISA | PASS | ARMv7 application profile; ARM state; no ARMv8/NEON code |
| Dependencies | PASS | `libc.so`, `libdl.so`, `/system/bin/linker` exist in saved firmware |
| API17 imports | PASS | All undefined symbol names exported by saved target `libc.so` |
| Safety | PASS | No write, signal, ptrace, debuggerd, injection, or proc-mem path |
| Bounded reads | PASS | 128 entries, two attempts, maximum 10,272 target bytes |
| Synthetic tests | PASS | `make test safety` |
| Vehicle/emulator execution | NOT PERFORMED | Milestone explicitly offline only |
| Ready for separately authorized parked attempt | YES | Binary build/static audit complete; runtime syscall support still unknown |

`mc_devs` static VA `0x35acbc` matches the prior reconstruction: `0x403e9cbc - 0x4008f000 = 0x35acbc`. Only the static VA should be reused; the future reader plan derives a fresh PID, maps, load bias, and runtime cell.

## Reproducibility

NDK and artifact checksums, compiler build, full compiler command, ELF facts, import table, binary hash, and source hash are recorded in `research/carplay/registry-reader-armv7-build.md`. The executable is ignored local build output and was not committed. No NDK files were committed.

## Process outcome

No ADB, vehicle, `jmcs` process, iPhone, ptrace, debuggerd, target-memory access, firmware modification, or target installation was used. The first future execution may return `ENOSYS`; if it does, report unsupported and stop. Do not fall back automatically to ptrace.

## Next action

Review and authorize a separate parked-session attempt using the prepared, non-hardcoded procedure in `research/carplay/runtime-registry-reader.md`. Keep the iPhone disconnected. If the attempt returns `ENOSYS`, stop and separately review whether any other read-only approach is acceptable.
