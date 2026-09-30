# Step 40C — runtime patch lifecycle assessment

## Target facts

The inspected `jmcs` is ELF32 little-endian ARM EABI5, `ET_DYN`. Its `PT_LOAD` headers include an RX segment at VA `0`, file/memory size `0x33fb50`, alignment `0x1000`, and an RW segment at VA `0x341988`, alignment `0x1000` (parsed from the pinned local ELF header). These ELF alignments describe the file's load segments; they do not establish the runtime page size, VMA permissions, or safe patch lifecycle. The target Android 4.2.2 Bionic source declares `mmap2`, `mprotect`, `munmap`, `futex`, and ARM `cacheflush` ([source](https://android.googlesource.com/platform/bionic/%2B/android-4.2.2_r1/libc/SYSCALLS.TXT)). The saved firmware and previous registry-reader audit establish the API-17 ARMv7 environment; Honda's precise kernel source is not available.

| Primitive | Evidence class | Result |
|---|---|---|
| Bionic `mmap2`, `mprotect`, `munmap`, `futex`, ARM `cacheflush` declarations | SOURCE-CONFIRMED | Present in Android 4.2.2 tag; not proof of successful use on Honda |
| Exact Honda kernel accepts RX→RW→RX for the jmcs text page | UNKNOWN | No matching kernel source or runtime available |
| File-backed private mapping preserves backing file after COW write | HOST/POSIX expectation only | Not tested on Honda API 17 or exact kernel |
| Cache visibility on Honda ARM CPUs | UNKNOWN | No API-17 ARM emulator or exact kernel |
| Atomic/coordinated patch of the split Setup BL | UNKNOWN | No rendezvous; uncoordinated use is unsafe |
| Near veneer placement | UNKNOWN | Arithmetic proves range only, not free/usable memory |
| Teardown and page restoration after all failures | MODEL ONLY | No target mapping has been changed |

## Implemented scope

`page_model.py` contains checked ARM32 page-cover arithmetic and an in-memory W^X protection state model. `veneer_ranges.py` computes exact Thumb BL reach/intersection. `veneer_allocator_model.py` chooses gaps from a supplied synthetic mapping snapshot but does not reserve address space. `rendezvous_model.py` validates synthetic parked-thread sets, generation stability, saved PCs, and veneer lifetime; it does not park actual threads. Tests cover boundaries, overflow, arbitrary positive modeled granule, W^X rejection, Setup's split four-byte alignment, allocation/no-gap, incomplete/changing snapshots, in-range saved PCs, and delayed release. They do not call operating-system memory APIs or model a live transaction. We deliberately did not add a `RuntimePatchTransaction`: the unproven page, cache, and rendezvous primitives would make such a class misleading.

No QEMU/Android ARM emulator or API-17 runtime is installed. The controlled host is macOS and cannot validate Linux/Bionic/ARM permission behavior. No executable-page experiment was performed because it would not close the target-platform evidence gap.

## Lifecycle decision

An eventual transaction would need this strict sequence: bind exact process/ELF identity; prevent relevant threads from executing and prevent thread-set changes; snapshot original bytes and page permissions; reserve/verify a reachable veneer; make target and veneer writable but never writable+executable; write and verify; perform target-supported cache synchronization; transition to RX; verify; resume. Rollback must preserve a critical parked state if it cannot restore bytes, permissions, cache state, or thread safety. Teardown must re-rendezvous, restore and verify both callsites, synchronize caches, prove no in-flight veneer users remain, then unmap. Failure of any condition cannot be converted into an automatic retry using guessed state.

**Step 41 remains NO.** The biggest blocker is the absence of a validated all-thread rendezvous/saved-PC strategy coupled to exact target cache/protection semantics.

## Step 40D update

The official ADA01 source archive is **RELATED PLATFORM SOURCE** only (Linux 3.4.108, generic Tegra support, no VCM30T30 board source) versus the target's 3.1.10+ VCM30T30 kernel. Exact kernel config and target VM page size remain unrecovered. An official API-17 ARM image was obtained and checksum-verified, but both available Android emulator engines reject ARM guests on this Apple Silicon host, and generic QEMU lacks Goldfish. No executable-memory/runtime experiment ran. These results preserve the existing NO decision for Step 41; see the [Step 40D report](../../step-reports/40d-honda-kernel-and-api17-runtime.md).

## Step 40E update

The user confirmed the parked/disconnected preconditions, but host ADB listed one authorized device, but the fixed-operation collector's first read-only `uname -a` request failed with `error: closed`. No target state was returned and no capture phase ran. Read-only target mprotect/cache/rendezvous gates are still unknown/untested. Step 40F and Step 41 remain NO. See the [Step 40E report](../../step-reports/40e-readonly-runtime-preflight.md).
