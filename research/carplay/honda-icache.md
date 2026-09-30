# Step 40C — instruction-cache synchronization

## Evidence and boundary

The Android 4.2.2/API-17 Bionic syscall table exposes ARM `cacheflush(start, end, flags)` as its private ARM cache-flush syscall, alongside `mmap2`, `mprotect`, and `munmap` ([API-era Bionic `SYSCALLS.TXT`](https://android.googlesource.com/platform/bionic/%2B/android-4.2.2_r1/libc/SYSCALLS.TXT)). Upstream ARM Linux documents the interval as `[start,end)` with no alignment requirement and says flags must be zero; it routes this request to `do_cache_op` ([ARM kernel syscall implementation](https://android.googlesource.com/kernel/common/%2B/a00cecdaef2e83258821321419609189bde08342/arch/arm/kernel/traps.c)).

The kernel source is not Honda's exact 3.1.10-derived kernel tree. Honda's exact kernel source/config and API-17 ARM execution environment were unavailable. Therefore the ABI is **SOURCE-CONFIRMED for the Android 4.2.2 Bionic interface**, but behavior on the Honda kernel is **UNKNOWN**. The implementation does not call `cacheflush` or compiler cache builtins.

## Candidate ordering (not yet runtime-validated)

For any eventual text update the safe intended order is: park all threads that can execute the target range; change RX to RW (never RWX); write and verify; invoke the ARM cache operation over the exact changed half-open range with flags zero; restore RX; verify the restored protection and bytes; only then resume threads. Cache maintenance failure at any point must leave threads parked and enter a critical recovery state. Cache flushing does not solve concurrent instruction fetch or saved-PC hazards.

## Result

`ICACHE SYNC MODEL: SOURCE-CONFIRMED INTERFACE; TARGET EFFECT UNKNOWN`

No API-17 emulator/QEMU was available. Host cache behavior is not evidence for ARM instruction-cache coherency.
