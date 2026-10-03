# 43T1-R1 runtime feasibility analysis

**Review type:** scoped technical literature review, not a claim of target behavior.
**Searched:** 2026-10-03. Sources: tagged AOSP Gitiles, Arm ABI/architecture documentation, Apple Open Source CoreFoundation headers/source, and existing identity-checked ClarityLink firmware analyses. Android-specific conclusions are scoped to API 17 and the exact AOSP `android-4.2.2_r1` tag where that source is cited.

## Evidence labels

- `HONDA_CONFIRMED`: direct evidence from the preserved Honda firmware analysis or authorized observation, within the stated scope.
- `DOCUMENTED_ANDROID`: documented in the cited AOSP source/version; this does not imply Honda has unmodified code.
- `DOCUMENTED_ARM`: normative ARM architecture/ABI documentation.
- `LAB_CONFIRMED`: local synthetic test or model result only.
- `EXTERNAL_REFERENCE`: public reference useful for principles, not Honda proof.
- `UNKNOWN`: no sufficient evidence for the Honda runtime claim.

A label applies to each finding below. No result in this document establishes that Honda runtime writes or attachment are safe.

## Android 4.2.2 / API 17 and Bionic

- `HONDA_CONFIRMED` The reviewed receiver platform identity is Android 4.2.2 / API 17, ARM32, with the preserved Honda `jmcs` ELF identity recorded in the project evidence ledger. The device uses vendor firmware; AOSP is a reference baseline.
- `DOCUMENTED_ANDROID` The AOSP `android-4.2.2_r1` tag is an Android 4.2.2 release tag. Its Bionic linker is the older `linker/` implementation (`linker.cpp`, `linker_phdr.c`, `dlfcn.c`), not today's linker. See [AOSP 4.2.2 tag](https://android.googlesource.com/platform/bionic/%2B/android-4.2.2_r1) and [tagged linker directory](https://android.googlesource.com/platform/bionic/%2B/android-4.2.2_r1/linker).
- `DOCUMENTED_ANDROID` Tagged `dlfcn.c` provides `dlopen`, `dlclose`, `dlsym`, `dlerror`, and `dladdr` wrappers. The public header and exact implementation must both be checked before relying on a symbol or handle. The modern documentation's API-22 load-order change and API-23 path behavior postdate API 17 and are not assumptions for this target. [API-17 `dlfcn.c`](https://android.googlesource.com/platform/bionic/%2B/android-4.2.2_r1/linker/dlfcn.c), [API-17 linker](https://android.googlesource.com/platform/bionic/%2B/android-4.2.2_r1/linker/linker.cpp), [Android linker behavior-change notes](https://android.googlesource.com/platform/bionic/%2B/786484d808704aac1a00e4b84b50486d62d4b33d/android-changes-for-ndk-developers.md).
- `DOCUMENTED_ANDROID` API-17 linker source walks ELF program headers, reserves/maps load segments, applies architecture-specific relocations, and performs mapping protection operations. This documents normal shared-object loading, not a public API for modifying another thread's code or installing a runtime patch. [Tagged ELF mapping code](https://android.googlesource.com/platform/bionic/%2B/android-4.2.2_r1/linker/linker_phdr.c), [tagged relocation code](https://android.googlesource.com/platform/bionic/%2B/android-4.2.2_r1/linker/linker.cpp).
- `DOCUMENTED_ANDROID` AOSP API-17 Bionic syscall metadata includes `mmap`, `mprotect`, and signal calls, but API presence says nothing about target process permissions, SELinux/vendor policy, page sharing, or an authorized attachment method. [API-17 syscall declarations](https://android.googlesource.com/platform/bionic/%2B/android-4.2.2_r1/libc/SYSCALLS.TXT).
- `DOCUMENTED_ANDROID` ARM instruction-cache synchronization in Android toolchains can use the ARM cacheflush system call (`__ARM_NR_cacheflush`); AOSP/compiler runtime source shows the call convention and that the operation can fail. It is not a general atomic-patch primitive and does not stop threads from fetching a partially changed instruction. [Android compiler-rt clear-cache implementation](https://android.googlesource.com/toolchain/compiler-rt/%2B/release_36/lib/builtins/clear_cache.c), [ARM syscall declaration](https://android.googlesource.com/platform/bionic/%2B/android-4.2.2_r1/libc/SYSCALLS.TXT).
- `DOCUMENTED_ANDROID` API-17 Bionic signal interfaces are POSIX-style `sigaction` calls. A signal facility is not evidence that safely stopping every receiver thread, preserving all signal dispositions, or resuming at a valid instruction boundary is possible. [API-17 signal declarations](https://android.googlesource.com/platform/bionic/%2B/android-4.2.2_r1/libc/include/signal.h).
- `HONDA_CONFIRMED` Existing Honda static ELF evidence identifies the Setup call path and Thumb callsite in the preserved binary. `HONDA_CONFIRMED` does not extend to live load bias, runtime mapping, mutable page permissions, process attachment, safe thread rendezvous, cache completion, or fault recovery; these remain `UNKNOWN`.

## ARMv7, ELF32, Thumb, and cache behavior

- `DOCUMENTED_ARM` AAPCS32 specifies the procedure-call contract including register roles, stack discipline/alignment, and callee/caller preservation. A trampoline must preserve the actual ABI state and instruction-set state for its concrete callsite; matching a C prototype alone is insufficient. [Arm AAPCS32](https://github.com/ARM-software/abi-aa/blob/2020Q2/aapcs32/aapcs32.rst).
- `DOCUMENTED_ARM` AAELF32 specifies ARM ELF object conventions and relocations. A copied or relocated instruction sequence cannot be presumed position-independent: PC-relative branches/literals require correct relocation or a proven alternative. [Arm AAELF32](https://github.com/ARM-software/abi-aa/blob/2020Q2/aaelf32/aaelf32.rst).
- `DOCUMENTED_ARM` Thumb instructions have instruction-size and branch-range constraints; the project's decoder/model computes the analyzed Thumb `BL` target and continuation from recorded bytes. `LAB_CONFIRMED` independent local models/tests agree on the preserved static artifacts. Neither fact establishes runtime address mapping or safe concurrent replacement.
- `DOCUMENTED_ARM` Architecture cache maintenance defines distinct data-cache clean, instruction-cache invalidate, and synchronization/barrier operations; required sequence and scope depend on architecture and shareability. A flush call is not an atomicity or mutual-exclusion guarantee. [Armv7-A/R Architecture Reference Manual](https://documentation-service.arm.com/static/5f8daeb7f86e16515cdb8c4e).
- `LAB_CONFIRMED` Existing tests exercise simulated RW→RX protection sequencing, failure injection, branch range, rendezvous evidence validation, and exact byte restoration in host memory. They do not execute on ARMv7/API 17, model microarchitectural instruction fetch, or prove Honda cache behavior.
- `UNKNOWN` Actual Honda cache maintenance support/result, instruction/data cache topology, SMP visibility, patch-store atomicity, page permission transitions, remote thread state, signals, and recovery following a fault or power loss.

## Bionic linker and dynamic loading

- `DOCUMENTED_ANDROID` API-17 AOSP supports the older `dlopen`/`dlsym` family and ELF relocation machinery. The Android 4.2 linker source is concrete evidence for that AOSP revision only; no API-22+ breadth-first lookup, API-23+ path handling, linker namespaces, or modern linker configuration is assumed.
- `HONDA_CONFIRMED` Existing firmware evidence finds Honda exports such as `dladdr` in its archived runtime library and distinguishes exported dynamic symbols from `jmcs`-local symbols. This does not mean a local function is resolvable by `dlsym` or that dynamic loading is an acceptable attachment path.
- `UNKNOWN` Honda's precise linker build, vendor patches, symbol resolution behavior at the candidate callsite, loaded-library side effects, constructor/destructor behavior, and whether loading a helper can be done without persistent or unrelated effects. No runtime load experiment is proposed by R1.

## CFLite / CoreFoundation ownership

- `EXTERNAL_REFERENCE` Apple's public CoreFoundation API defines Create/Copy ownership conventions and `CFRetain`/`CFRelease` reference counting. Collection callback tables control whether collection insertion retains/releases its keys/values; dictionary/array mutability is explicit in the API. Public headers describe immutable copies and mutable copies. [Apple CFDictionary API/header](https://github.com/apple-oss-distributions/CF/blob/main/CFDictionary.h), [Apple CFArray API/header](https://github.com/apple-oss-distributions/CF/blob/main/CFArray.h), [Apple CFRuntime implementation](https://github.com/apple-oss-distributions/CF/blob/main/CFRuntime.c).
- `HONDA_CONFIRMED` Static Honda firmware evidence traces a synchronous response serialization path, several callback wrapper functions/tables, and Type110 container operations. The exact constructor callback arguments for every Setup response/array/entry path remain partial or unresolved in the existing ownership ledger. See [Honda CF callback evidence](../carplay/honda-cf-callback-ownership.md).
- `LAB_CONFIRMED` PREP2's `FakeCF`/bridge tests exercise explicit retain/release, copy-on-write preparation, rollback, and ownership errors under its local semantics. These are contract tests for the model only.
- `UNKNOWN` Honda CFLite version/source parity with Apple's implementation; response dictionary and array callback identity at every constructor; getter ownership (+0/+1); Type111 dictionary/number/entry lifetime; custom callback corner cases; mutation visibility and concurrency; behavior under serializer failure; and freedom from Honda-specific changes. Apple's behavior is not silently transferred to Honda.

## Reversible instrumentation and fault containment principles

- `EXTERNAL_REFERENCE` The reviewed primary architecture/ABI references support engineering constraints: decode/relocate every overwritten instruction, preserve ABI/ISA state, synchronize caches for the actual platform, and verify memory independently after restoration. These are principles, not copied patch code or a target result.
- `LAB_CONFIRMED` Host/synthetic models cover compare-before-change, exact expected bytes, refuse-on-foreign-bytes, simulated cleanup ordering, generation-scoped resource cleanup, and restoration checking. The models cannot establish atomicity or recover from a real process/host/power failure.
- `UNKNOWN` A same-process rollback cannot run after process termination; a host controller cannot guarantee an attached target remains reachable; a reboot can discard volatile code but does not prove the receiver restarted normally or restored stock behavior. Only a separately observed post-restart check can prove that later state.
- `UNKNOWN` No offline source can prove arbitrary target crash-freedom or physical stock behavior. Such claims require target-specific evidence and must remain outside the offline proof boundary.

## Object-boundary inventory

| Object | Conservative status before target-specific proof | Required contract / unresolved evidence |
|---|---|---|
| Setup response | borrowed Honda pointer; synchronous use only | Honda static caller owns/releases after serializer. No retention past call. |
| `CFDictionary` and `CFArray` from Honda | borrowed, mutable state unknown at bridge boundary | Do not mutate original graph until all callbacks/getter ownership are proven. Use candidate copies; exact callback ownership remains unresolved. |
| Type111 entry/numbers/keys | project-created, project-owned until explicit insertion proof | Treat callback retain as unknown. Do not release local refs or publish child until insertion ownership is proven. |
| Serializer inputs | borrowed for synchronous serializer window | Exactly one stock serializer invocation; no retained references after return unless independently retained and documented. |
| Transaction context | project-owned, immutable generation token | Must outlive synchronous callback and serialize/deinit; do not let stale callbacks reach a later generation. |
| Listener / accepted socket / worker | project-owned by exactly one generation | Generation cleanup closes accepted socket, listener, worker and private state once; no Honda-owned FD teardown. |
| Generation | project transaction-owned | Exact-generation equality required on every completion and cleanup; stale generation cannot mutate or close current one. |
| Response/bridge failure | unknown target semantics | Failure is not success; stock response and object lifetimes must be independently checked. |

## R1 conclusion

`RETURN_TO_OFFLINE_WORK`. Research improves the assumptions list but does not prove the Honda vendor runtime, arbitrary CF ownership, safe page permissions, thread quiescence, atomic Thumb replacement, runtime attachment, or crash/power recovery. The new verifier and state machine are executable host logic only. The next useful work is an API-17 ARM/Bionic compatibility harness and a static CFLite/Setup constructor audit from preserved artifacts, with strict labels distinguishing generic AOSP/Apple behavior, lab models, and Honda evidence.

## References

1. AOSP, Bionic `android-4.2.2_r1` tag, linker, libc, syscall declarations: links above; exact historical source.
2. Arm, AAPCS32 2020Q2 and AAELF32 2019Q1, ABI specifications.
3. Arm, ARMv7-A/R Architecture Reference Manual, cache maintenance and synchronization architecture.
4. Apple Open Source CoreFoundation, public collection/runtime headers/source; modern public implementation used only as external reference.
5. ClarityLink preserved evidence: `research/carplay/honda-cf-callback-ownership.md`, `research/carplay/honda-response-ownership.md`, `research/platform/api17-arm-runtime.md`, and related linked step reports.

