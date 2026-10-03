# 43T1-R2 — API-17 ARM/Bionic patch hazard harness

**Scope:** offline source review and host-only simulation. No process, device, memory, or listener backend exists in the harness.

## Evidence labels

`HONDA_CONFIRMED` means static findings in the preserved, hash-identified `jmcs` artifact or a recorded observation, only within that scope. `AOSP_API17_DOCUMENTED` is the tagged Android 4.2.2 / API 17 source, not Honda vendor behavior. `ARM_DOCUMENTED` is an ARM architecture/ABI requirement. `APPLE_CF_REFERENCE` is reference material and never proof about CFLite. `LAB_CONFIRMED` is a local host-only test. `MODEL_ONLY` is an abstract simulation. `INFERENCE` is a conclusion from labeled facts. `UNKNOWN` is not established.

## Versions and sources reviewed

- `AOSP_API17_DOCUMENTED` Android 4.2.2 tag `android-4.2.2_r1`: [Bionic linker](https://android.googlesource.com/platform/bionic/%2B/android-4.2.2_r1/linker), [linker/dlfcn.c](https://android.googlesource.com/platform/bionic/%2B/android-4.2.2_r1/linker/dlfcn.c), [linker/linker_phdr.c](https://android.googlesource.com/platform/bionic/%2B/android-4.2.2_r1/linker/linker_phdr.c), [libc syscall table](https://android.googlesource.com/platform/bionic/%2B/android-4.2.2_r1/libc/SYSCALLS.TXT), and [signal.h](https://android.googlesource.com/platform/bionic/%2B/android-4.2.2_r1/libc/include/signal.h).
- `AOSP_API17_DOCUMENTED` compiler-rt `release_36` [ARM clear-cache implementation](https://android.googlesource.com/toolchain/compiler-rt/+/release_36/lib/builtins/clear_cache.c). This describes that toolchain implementation, not the exact Honda libc/compiler runtime.
- `ARM_DOCUMENTED` [AAPCS32 2020Q2](https://github.com/ARM-software/abi-aa/blob/2020Q2/aapcs32/aapcs32.rst), [AAELF32 2019Q1](https://github.com/ARM-software/abi-aa/blob/2019Q1/aaelf32/aaelf32.rst), and [ARMv7-A/R Architecture Reference Manual](https://documentation-service.arm.com/static/5f8daeb7f86e16515cdb8c4e).
- `APPLE_CF_REFERENCE` Apple public [CFArray](https://github.com/apple-oss-distributions/CF/blob/main/CFArray.h), [CFDictionary](https://github.com/apple-oss-distributions/CF/blob/main/CFDictionary.h), and [CFRuntime](https://github.com/apple-oss-distributions/CF/blob/main/CFRuntime.c) sources are conceptual references only.
- `HONDA_CONFIRMED` Preserved firmware findings are cross-referenced in [R1 feasibility analysis](runtime-feasibility-analysis.md), [R1 report](../../step-reports/43t1-r1-runtime-feasibility-review.md), [thread rendezvous analysis](../carplay/honda-thread-rendezvous.md), and [Thumb callsite record](../carplay/honda-thumb-hook.md).

## API-17 facts and limits

- `AOSP_API17_DOCUMENTED` The tag contains the older Bionic `linker/` implementation, including `dlopen`/`dlsym` wrappers, ELF mapping/relocation logic, `mmap2`, `mprotect`, signal-related system interfaces, and ARM `cacheflush` syscall metadata. These establish interfaces in that source revision only. They do not establish process permissions, SELinux/vendor policy, mapping layout, or a safe way to modify code in Honda's process.
- `INFERENCE` Presence of `mprotect`, signals, or `cacheflush` is not evidence of safe all-thread rendezvous or atomic multi-instruction replacement. A cache operation addresses visibility/order requirements; it cannot make two separate stores indivisible.
- `AOSP_API17_DOCUMENTED` compiler-rt `release_36` shows an ARM cacheflush path and handles failure. Its existence supports modeling cache-sync success/failure as distinct events. It is not evidence that the exact Honda build calls this implementation or that every core has completed synchronization.
- `ARM_DOCUMENTED` AAPCS32/AAELF32 constrain register/stack/relocation behavior. They do not prove an arbitrary four-byte instruction replacement is atomic. Cache maintenance and synchronization have architecture- and scope-specific requirements; a successful cache event does not stop a thread already executing or fetching the patch span.
- `HONDA_CONFIRMED` Static artifact evidence records Setup callsite `0x28af72`, bytes `fa f7 b5 fa`, target `0x2854e0`, continuation `0x28af76`. The address is 2 mod 4 and the four-byte interval crosses the model's four-byte fetch-group boundary.
- `UNKNOWN` Honda runtime load bias, page mapping/protection behavior, CPU fetch behavior at this location, atomic-store guarantee, thread set, signal/rendezvous behavior, cache completion, interruption recovery, and independent restoration remain unproved. A four-byte fetch group is treated as a risk geometry, not a universal claim about every ARM implementation.
- Android API-22/API-23+ linker behavior is intentionally excluded from API-17 conclusions.

## Harness model

`MODEL_ONLY` `src/claritylink-honda/runtime_safety/thumb_patch_model.py` models the recorded BL bytes, target and continuation, fetch-group crossing, affected page cover, both orders of two halfword writes, each mixed state, modeled RW/RX and cache events, interruptions, cache failure, and exact restoration of model-generated states. The thread rendezvous checker validates a proposed snapshot but does not stop threads. The experiment-authority transition always fails.

`LAB_CONFIRMED` Focused tests check the Honda geometry and an aligned comparison site; either halfword first; write/cache/protection/readback order; interrupt before and after modeled cache synchronization; cache-sync failure; interrupted restoration; idempotent restore; refusal to overwrite foreign bytes; and incomplete/changing-thread snapshots. The source AST test rejects imports of process/device I/O backends. All state is a local `bytearray`.

`MODEL_ONLY` Permission and cache labels are events, not syscalls. The model does not emulate instruction prefetch, CPU pipelines, real scheduler races, signal delivery, ARM cache hierarchy, page tables, or a target fault. Its successful restore test shows only that this software model can restore its own known bytes under its modeled assumptions.

## Decision-relevant result

`LAB_CONFIRMED` Either write order creates a mixed 32-bit instruction state between stores, even at a fetch-group-aligned comparison site. The actual Honda callsite additionally crosses the configured fetch-group boundary. An executing thread can therefore encounter old, new, or mixed bytes unless a complete stop and resume protocol is proven.

`INFERENCE` The current four-byte inline patch requires a proven all-thread stop/re-entry protocol, safe PC exclusion, stable thread membership, cache completion, and independent restoration. None is established for Honda. The strategy remains no-go pending proof; cache flush, page permission sequencing, and this model do not close the gap.

## Unknowns that remain

1. Whether Honda's exact ARMv7 CPU and kernel can rendezvous every relevant thread without deadlock or signal side effects.
2. Whether thread membership stays stable and every saved PC can be excluded from the patch span through both patch and restore.
3. The exact writable/executable mapping policy and cache maintenance outcome for Honda `jmcs`.
4. An atomic mechanism, if any, for the complete replacement, and an independent restoration/readback path after host loss, process restart, or interrupted restore.
5. Serializer/callback re-entry and concurrent mutation during any prospective response update.

No runtime experiment is implied or authorized by this note.
