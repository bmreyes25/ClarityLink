# One-shot `jmcs` runtime registry reader

Offline implementation only. This program has not been run on the Honda, and no ADB/iPhone/vehicle interaction is part of this milestone.

## Contract and safety

The target is accepted only when `/proc/<pid>/cmdline` is exactly `/system/bin/jmcs`; PID disappearance or a different command line aborts. The reader obtains readable ranges from `/proc/<pid>/maps` (or the optional `--maps` file), and validates every target range before each read. Use the live maps default for target execution. It reads the 32-bit cell, manager `+8`, each 12-byte node, and each 8-byte interface. It follows only `next`; bookkeeping is reported as an opaque word.

Reads use only `process_vm_readv`, through the syscall number supplied by the target system headers (`SYS_process_vm_readv` or `__NR_process_vm_readv`). Build fails if neither is defined; no syscall number is guessed. `ENOSYS` is `READ_STATUS=UNSUPPORTED`; `EPERM`/`EACCES` are `PERMISSION_DENIED`; `ESRCH`, `EFAULT`, `EINVAL`, short reads, and invalid mappings are reported distinctly. There is no ptrace fallback.

The source contains no target-write API, `ptrace`, signal, debuggerd, register, breakpoint, injection, or `/proc/<pid>/mem` path. It does not call either callback. Its only `write` usage is stdout/stderr output. The only target operation is `process_vm_readv`.

It compares manager/head and node address, next, and interface across immediate complete passes. There are at most two snapshot attempts (four walks). An inconsistent final result is discarded. A candidate list is capped at 128; null/unaligned/invalid addresses and cycles abort. Requested/read byte counts are cumulative across attempts. Worst case: `2 attempts × 2 passes × (8 + 20×128) = 10,272` bytes requested/read; a single successful attempt uses at most 5,136 bytes. No page-sized reads occur.

## Build

`make test` runs the synthetic backend, which never accesses another process. `make jmcs-registry-reader` builds a host binary only on a Linux host with headers that define the syscall ABI. `make armv7 ARM_CC=<compiler>` requests PIE ARMv7 output, but requires an installed compiler/sysroot whose headers define the target syscall ABI. No ARMv7 Android compiler/sysroot is configured in the current environment, so target build compatibility remains unverified.

Intended ABI is 32-bit ARM EABI (armeabi-v7a). The dynamic build requires the Android Bionic libc providing `syscall`, procfs, and the usual C runtime; a static build is not selected because availability/compatibility with the actual Honda Android userspace is unverified. `process_vm_readv` was added to mainline Linux after the likely 3.1-era target kernel; it may be absent unless backported. Its target availability and caller permission are unknown. Unsupported/denied means stop.

## Invocation shape (future only; do not execute in this milestone)

```sh
jmcs-registry-reader --pid <fresh-pid> --mc-devs-cell <fresh-runtime-address>
```

`--maps <file>` can supply a saved maps snapshot for offline review; a future live invocation should omit it and validate against the current `/proc/<pid>/maps`. Do not install under `/system`. The likely temporary destination is `/data/local/tmp`, subject to a future parked-session check of writable/executable policy. A future workflow should push one temporary executable, run once, pull only its small JSON, delete both temporary files, and confirm `jmcs` remains running. No command in this section has been executed.

## Output/resolution

Success is compact JSON with pointer strings in traversal order and requested/read totals. Callback fields are addresses only. Module attribution from the reader is a coarse mapped/unmapped label; resolve against the same-session saved maps and ELF files on the Mac with:

```sh
python3 research/tools/resolve_runtime_registry.py reader.json jmcs-maps.txt --module-dir path/to/saved/elves
```

The resolver reports runtime address, mapped path, derived load bias when ELF program headers are available, static VA/offset, nearest preceding symbol when `nm` is available, and `addr2line` function/DWARF line where available. Missing ELF/debug data remains unresolved.
