# Step 41B — jmcs load seam and dladdr

**Status: linker export question answered; no existing Honda load seam proven.** Offline against preserved filesystem, exact tagged AOSP source, existing tracked static analysis, and public prior art. No vehicle, ADB, `su`, binary execution/emulation, firmware modification, deployment, injection, or Type111 activation.

## Findings

1. AOSP `android-4.2_r1` ARM table definitively has `dladdr` and `dl_unwind_find_exidx`, not `dl_iterate_phdr`. `dladdr` uses `find_containing_library` and reports soinfo filename/base.
2. Honda archived `/system/lib/libdl.so` dynsym matches the six AOSP ARM loader names exactly. Hash `1e44ed53cb5238de749d2f4cddc43bbe2026aa9d531a9c5446f39bbfe8c3aab6`. Honda linker strings contain `dladdr`, unwind symbol, `LD_PRELOAD`, `LD_LIBRARY_PATH`, and `libdl.so`; linker hash `608af427ac43a316471e5adc18e25f6d3c9ac5e4ec2c04f19561ee774357aa90`. Export set is HONDA CONFIRMED; function-level semantic identity to AOSP remains high-confidence because linker is stripped and no disassembler was available.
3. Honda `jmcs` is ARM32 ET_DYN (PIE-style), entry VA `0x13100`, executable PT_LOAD `(offset=0, vaddr=0, filesz=0x33fb50, memsz=0x33fb50, RX, align=0x1000)` and RW segment `(offset=0x340988, vaddr=0x341988, filesz=0xfdac, memsz=0x2e60c, RW, align=0x1000)`. Load bias can be derived from the exact executable mapping and matching PT_LOAD. Its prior exact hash remains `cbc7ba...51c232`.
4. `libcarplay_proxy.so` is a direct `DT_NEEDED` dependency of jmcs, SONAME `libcarplay_proxy.so`, so it loads before receiver session Setup. Its exports provide a valid pointer source for identifying the proxy with dladdr. It is a singleton Honda callback boundary, not a plugin loader.
5. The preserved extracted filesystem contains no `init.rc`/`init.*.rc` file; no service invocation, wrapper, environment, property trigger, account/groups, rlimits, or SELinux label could be verified. The jmcs process starts as `/system/bin/jmcs` using `/system/bin/linker`, but its init ancestry is UNKNOWN. Therefore no exact existing configurable load seam or exact edit location is proven.
6. jmcs direct dependencies and generic SQLite extension-loading calls are documented. No code/config evidence establishes SQLite extension loading as a legitimate user-controlled CarPlay plugin path. Do not exploit it.
7. `LD_PRELOAD` is technically supported in AOSP 4.2 and Honda linker has the environment string. Honda's effective startup environment and a Honda init configuration path that can set it are UNKNOWN. It is the narrowest future design candidate if the actual service declaration is later obtained.
8. Honda Setup and `/info` callsites are direct Thumb BL instructions, so generic LD_PRELOAD symbol substitution does not observe those internal edges. The existing narrow callsite-hook model remains the likely route after in-process entry; no patch is implemented.

## Pointer and self-location model

- `dlopen("libcarplay_proxy.so", RTLD_NOW)` + `dlsym(handle,"mc_carplay_proxy_screen_register")` supplies a pointer in the proxy, whose exact exported symbol is Honda-confirmed.
- Useful jmcs receiver functions are not dynsym exports; `AirPlayCopyServerInfo` is absent `.dynsym`. `RTLD_DEFAULT`/`RTLD_NEXT` cannot be assumed to reveal it.
- Exact `/proc/self/maps` pathname + offset-zero executable mapping + pinned jmcs PT_LOAD/hash is the best main-executable location path. This does not need another process's maps. It is designed and host-modeled, not accessed on the target.
- `dladdr` semantic equivalence is HIGH CONFIDENCE but not binary-semantic proof; exact Honda export presence is YES.

## Load seam conclusion

No existing stock plugin or Honda-configured preload seam was found. **The smallest future persistent change is conditionally one `setenv LD_PRELOAD <absolute hash-pinned library>` service option in the actual jmcs init service**, plus staging one library. The exact service file and line are missing from this archive, so this is a bounded design candidate, not a proven exact modification. Root/reboot likely; recovery policy, writable location, and actual init support still require evidence. A separate deployment approval is mandatory.

## Decision gate

```text
AOSP 4.2 ARM DLADDR: YES
HONDA DLADDR: YES (export); returns module base: UNKNOWN at exact Honda implementation level, HIGH-CONFIDENCE AOSP match
AOSP 4.2 ARM DL_ITERATE_PHDR: NO
HONDA DL_ITERATE_PHDR: NO
JMCS ELF: ARM32 ET_DYN PIE-style, entry 0x13100, executable PT_LOAD at VA/file offset zero
JMCS SELF-LOCATION: READY (bounded self-maps + exact ELF/hash design; runtime not exercised)
CARPLAY MODULE SELF-LOCATION: READY (proxy dynsym pointer + dladdr design; runtime not exercised)
/PROC/SELF/MAPS FALLBACK: READY (bounded offline parser; target policy untested)
EXTERNAL PRIVILEGED MAPS REQUIRED: NO
JMCS STARTUP PATH: /system/bin/linker -> /system/bin/jmcs; init service/environment ancestry absent from archive
LIBCARPLAY_PROXY LOAD MECHANISM: direct jmcs DT_NEEDED, before Setup
LIBCARPLAY_PROXY NATURAL SEAM: PARTIAL
EXISTING JMCS PLUGIN/DLOPEN SEAM: NO proven CarPlay seam; generic SQLite extension only
LD_PRELOAD TECHNICALLY SUPPORTED: YES
LD_PRELOAD EXISTING HONDA CONFIG SEAM: UNKNOWN
BEST IN-PROCESS LOAD SEAM: none proven; conditional init-service LD_PRELOAD setting is the smallest future change
LOAD SEAM PROVEN: NO
PERSISTENT CHANGE REQUIRED TO LOAD CLARITYLINK: YES (no existing seam found)
MINIMUM FUTURE PERSISTENT CHANGE: one LD_PRELOAD service option and one staged immutable library; exact init file unknown
STOCK SETUP CALLABLE FROM INTERPOSER: YES, via validated direct-address/callsite plan; runtime shim not built
SETUP CALL BINDING: DIRECT
PROLOGUE HOOK LIKELY REQUIRED: NO for selected BL callsite model; a callsite shim still requires future patch safety
HONDA R15 FINGERPRINTS: PARTIAL
STEP 40F: OBSOLETE AS PREREQUISITE
STEP 41: NOT READY
TYPE111 NEGOTIATION IMPLEMENTATION: NOT READY
LIVE TEST: NOT READY
BIGGEST BLOCKER: the exact jmcs init service/configuration source needed to prove or create a controlled preload seam is absent from the preserved archive
NEXT ACTION: acquire the matching archived init service declaration and verify whether it supports a reversible setenv LD_PRELOAD option
```

## Validation

The new standard-library smoke suite passed: maps parsing, offset/bias correlation, duplicate mapping, malformed/truncated inputs, dladdr success/null/wrong module/wrong base/pointer checks, target hash, and load-seam fail-closed cases. Python compileall and `git diff --check` passed. Pytest remains unavailable; no global package was installed. No third-party code was cloned into the repository.
