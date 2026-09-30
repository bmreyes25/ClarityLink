# Executable memory and cache synchronization — Step 40C

## What is established

The offline patch model changes bytes in a Python bytearray only. Unicorn maps synthetic code as emulator memory; that is not a target OS mapping or permission transition. The pinned `jmcs` ELF is ELF32 little-endian ARM EABI5 ET_DYN. Its RX PT_LOAD is VA 0, size `0x33fb50`, alignment `0x1000`; its RW PT_LOAD is VA `0x341988`, alignment `0x1000`. Segment alignment is not runtime page-size evidence.

Android 4.2.2/API 17 Bionic `SYSCALLS.TXT` exposes `mmap2`, `mprotect`, `munmap`, `futex`, and ARM `cacheflush(start,end,flags)`. Upstream ARM kernel source documents the cacheflush range as half-open and requires zero flags. Honda's exact 3.1.10-derived kernel source/config was unavailable, so API/kernel behavior for Honda remains unverified. See [cache synchronization](honda-icache.md) and [thread rendezvous](honda-thread-rendezvous.md).

## Unknowns blocking a live hook

- Whether any page can actually be allocated within the common `BL` range; arithmetic alone is recorded in [veneer allocation](honda-veneer-allocation.md).
- Whether the target platform permits a safe W^X transition for the relevant page and how to restore the original permissions on every failure path.
- How all threads that could execute either call site are coordinated during replacement and restoration.
- Whether the API-era ARM `cacheflush` interface behaves as expected on Honda's exact kernel and all relevant cores.
- How original page protections and veneer allocation are verified/released after restoration.
- What recovery remains possible if protection restoration, cache synchronization, verification, or process identity checks fail.

No permanent RWX assumption is made. No executable-memory API is called by this project code. Host code tests only pure page arithmetic/W^X state and BL ranges. No API-17 ARM emulator or runtime is available. `ICACHE SYNC MODEL: SOURCE-CONFIRMED INTERFACE; TARGET UNKNOWN`; `MEMORY PROTECTION MODEL: HOST MODEL ONLY`. Step 41 stays NO until target page/cache semantics and a complete all-thread rendezvous/restore path are validated.
