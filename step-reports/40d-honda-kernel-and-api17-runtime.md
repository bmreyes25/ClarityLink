# Step 40D — Honda kernel provenance and API-17 ARM lab

**Scope:** offline/lab only. No vehicle connection, ADB, live `jmcs`, ptrace, partition writes, hooks, iPhone, or Type111 activity occurred. No native test binary or emulator guest was run.

## Results

### Source and binary provenance

The official Honda/Panasonic ADA01 page linked the source archive; the HTTPS download was 165,009,002 bytes, SHA-256 `a795665d31cc563c09e907cf4de3c1a489262e90a42667568fd05990e9945a9b`. Safe ZIP inventory found 50,885 entries / 635,746,711 expanded bytes, with no unsafe paths, symlink escapes, or special files. It was extracted outside Git with path and CRC checks; no build scripts were run.

ADA01 contains generic Tegra2/3 support, but its kernel source identifies Linux 3.4.108 and has no `vcm30t30`/MY16ADA board implementation. The exact forensic image identifies Android 4.2.2/API 17, `Honda/Andromeda/vcm30t30a`, model MY16ADA, and kernel `3.1.10+`. Target boot image SHA-256 is `37d928201d8861e3037c3e9be8254617eeadfe09e018e37a46500d0711d875cc`; the copy-extracted kernel payload SHA-256 is `1dd3e403311d5cd18f12284b2d9263a0999707f1f16d3d83df1d8c324428949a`. Module vermagic supports `3.1.10+ SMP preempt mod_unload ARMv7`. ADA01 therefore ranks **RELATED PLATFORM SOURCE**, not exact or demonstrated family source.

Exact config could not be recovered: apparent IKCFG markers do not enclose the expected gzip stream, and no captured `/proc/config.gz` is available. ADA01's generic `tegra_defconfig` is candidate-only. Target VM page size remains unknown; the boot-image 2,048-byte alignment is not a VM granule measurement. Details and comparison are in [source assessment](../research/platform/honda-ada01-source.md), [binary provenance](../research/platform/honda-kernel-provenance.md), and [config recovery](../research/platform/honda-kernel-config.md).

### API-17 ARM execution lab

The official Google API-17 ARM EABI-v7a image was downloaded and matched its repository SHA-1 (`a18a3fd0958ec4ef52507f58e414fc5c7dfd59d6`); archive SHA-256 is `f6953289a7e2bd2fd9a6418afe445a7f3dde4e07dcdbbdfa1b80c9cf5abcef93`. The official macOS x86_64 Android Emulator package was also verified from Google's package metadata. On Apple Silicon its QEMU2 engine rejects ARM and classic-engine selection also exits with the same unsupported ARM fatal. Generic `qemu-system-arm` lacks the API-17 image's Goldfish machine. We stopped after these distinct supported-path checks instead of repeatedly trying the same unsupported runtime.

Consequently no ARM/API17 executable ran: no `uname`, process maps, page size, memory protection, cacheflush, Thumb execution, file-backed mapping, signals, futex, saved-PC, veneer, or rendezvous test occurred. No RX→RW→RX behavior is inferred from host tests. Runtime details are in [API-17 ARM runtime](../research/platform/api17-arm-runtime.md).

### Source-only kernel paths

The ADA01 3.4.108 ARM cacheflush path in `arch/arm/kernel/traps.c` calls `do_cache_op`; that candidate function rejects reversed ranges/nonzero flags, clips to the VMA, and calls `flush_cache_user_range`, with generic ARMv7 range handling in `cacheflush.h`/`cache-v7.S`. Candidate `mm/mprotect.c` validates page alignment, length overflow, `VM_MAY*`, security hooks, and applies changes via `mprotect_fixup`. These observations are from a nonmatching source tree and do **not** establish Honda behavior. Thus Honda-source cacheflush is partial comparison evidence and Honda-source mprotect is unavailable as target evidence. Neither changes Step 40C's unknown target gate.

### Safety/lifecycle decisions

- Persistent RWX: **NO**.
- Honda in-process code loading: **NOT PROVEN; OUT OF SCOPE**.
- Thread rendezvous remains not ready. No thread creation race or saved-PC validation is handled by the host model as an actual process operation.
- Step 41 remains **NO**. The exact target page/cache/protection semantics and a safe all-thread rendezvous are still not validated.
- Step 40E is appropriate as the next milestone: parked read-only target preflight only. This report does not perform or authorize it.
- Type111 remains **NO**.

## Verification

Maintained suites (host Python only):

| Suite | Result |
|---|---|
| `tests/honda` | 55 passed, 1 skipped |
| `tests/interposer` | 14 passed |
| `tests/transport tests/negotiation` | 47 passed, 31 subtests passed |
| `src/claritylink-renderer/tests` | 8 passed |

No API-17 emulator/runtime tests were available. These host results do not validate ARM or Honda runtime behavior.

ECC guidance was applied for evidence quality, archive safety, platform security, scope, tests, and final diff. The installed ECC capability in this session exposes skills, not an independent reviewer endpoint; this is a self-review, not an external ECC pass. No implementation code or downloaded third-party payload was committed.

## Decision gate

ADA01 SOURCE OBTAINED: YES

ADA01 PROVENANCE: OFFICIAL

ADA01 KERNEL VERSION: 3.4.108

TEGRA SOURCE PRESENT: YES

VCM30T30 SOURCE PRESENT: NO

HONDA SOURCE MATCH: RELATED

EXACT HONDA KERNEL CONFIG: NOT RECOVERED

EXACT HONDA KERNEL SHA256: `1dd3e403311d5cd18f12284b2d9263a0999707f1f16d3d83df1d8c324428949a`

TARGET PAGE SIZE: UNKNOWN

HONDA-SOURCE MPROTECT MODEL: UNAVAILABLE

HONDA-SOURCE CACHEFLUSH MODEL: PARTIAL

API17 ARM RUNTIME: NOT READY

REAL ARM THUMB EXECUTION: NOT AVAILABLE

ANONYMOUS RX-RW-RX: NOT AVAILABLE

FILE-BACKED PRIVATE RX-RW-RX: NOT AVAILABLE

CACHEFLUSH EXECUTION: NOT AVAILABLE

VENEER EXECUTION: NOT AVAILABLE

ABI PRESERVATION: PARTIAL

THREAD RENDEZVOUS: NOT READY

THREAD CREATION RACE: NOT HANDLED

SAVED-PC VALIDATION: NOT AVAILABLE

MULTITHREADED PATCH STRESS: NOT AVAILABLE

PERSISTENT RWX: NO

HONDA IN-PROCESS CODE LOADING: NOT PROVEN

@ECC REVIEW: OPEN FINDINGS

READY FOR STEP 40E READ-ONLY TARGET PREFLIGHT: YES

READY FOR STEP 41 NO-OP HOOK: NO

READY FOR TYPE111: NO

BIGGEST BLOCKER: No matching Honda 3.1.10+ VCM30T30 kernel source/config or bootable API-17 ARM guest is available to validate target W^X/cache behavior and an all-thread rendezvous.
