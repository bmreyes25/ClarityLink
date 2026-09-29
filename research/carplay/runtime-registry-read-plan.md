# Minimum read-only `mc_devs` observation plan

Date: 2026-09-29. Design only; no execution on the head unit.

## Objective and scope

Recover the manager pointer, registry head, bounded nodes, traversal ordinal, interface/context pointers, and candidate callback addresses. Stop after writing the compact derived observation. Resolve callback addresses and evaluate slot `+0` against the exact request `"CarPlay Screen"` on the Mac using the saved ELF. Do not collect scores during this first stage.

Known historical anchor: `jmcs` ELF load base `0x4008f000`; `mc_devs` cell ELF VA `0x35acbc`, prior runtime cell `0x403e9cbc`. Rediscover PID and mappings in execution. The older address is a guard, not a reusable PID/address assumption.

The saved ARM disassembly resolves the allocated 12-byte node: `+0` next, `+4` prior incoming-link location (list bookkeeping), `+8` interface. The callback's context argument is the interface pointer itself. Registration appends at the tail, so traversal order is chronological insertion order and the tie order. See [runtime-registry-layout.md](runtime-registry-layout.md).

## Mechanism comparison

| Mechanism | Supported on target | Pause/interruption | Target memory writes | Persistence | Risk / assessment |
|---|---|---|---|---|---|
| `process_vm_readv` | **Unknown** for this Android kernel/build and caller permissions; Linux API availability alone does not prove syscall enabled or permitted here. The prior `/proc/<pid>/mem` denial is not proof about this syscall. Check availability/permissions during a future approved parked session without falling back repeatedly. | Usually no intentional stop; concurrent list mutation can make a torn/inconsistent traversal. | No, read-only operation. | None. | Preferred first if supported. Validate mappings and short reads; note snapshot consistency as best-effort. |
| `ptrace` PEEKDATA-style read | **Unknown**; ptrace policy and capabilities were not established. Requires target-specific permission check. | Attach/stop behavior applies to traced thread; a complete consistent multithread snapshot may require stopping all `jmcs` threads, with careful detach/resume of each. PTRACE_SEIZE/INTERRUPT availability is unknown. | No, PEEKDATA reads only; do not use POKEDATA. | None. | Fallback only after exact thread lifecycle is reviewed and tested off-target. Main risk is leaving any target thread stopped. |
| Temporary debugger attach for memory reads | **Unknown/unavailable on recorded target setup**: no target `gdbserver`/`lldb-server` was available in the prior session; host debugger presence does not supply a target server. | Usually stops traced thread(s), adds debugger protocol and session complexity. | Reads need not write target memory, but debugger features can alter registers or state; must prohibit those operations. | No if cleanly detached; debugger-server installation would violate scope. | More moving parts than a purpose-built reader. Do not install a server or invoke `debuggerd`. |
| Instrumentation / hooking | Not needed for registry-only goal. | Can interrupt callbacks or change timing. | Common methods modify code/data or execution state. | Can persist until rollback/restart. | Excluded from stage one. More risk and work; only revisit a narrow score observation if offline static evaluation fails. |

**Recommendation:** attempt a single-purpose `process_vm_readv` reader first. It has the smallest interruption footprint if available and permitted. If unsupported/denied, stop and report; a ptrace PEEKDATA fallback requires a separately reviewed design, including how every thread will be resumed. Do not silently escalate to debugger attach or instrumentation.

## Execution envelope (future parked session)

- ARMv7 32-bit reader runs locally on the head unit; only opens `/proc` metadata for `/system/bin/jmcs` and performs bounded reads from that PID.
- No writes to target address space; no POKEDATA, breakpoints, injected code/library, register changes, configuration changes, install, persistent daemon/service, restart, or tombstone-generating operation.
- Discover PID by executable path, then read maps and verify base, readable mapping coverage, and current process identity. Read only the computed cell, manager head, visited node words, and callback words.
- Cap list at 128 nodes, validate non-null/aligned pointers and readable mappings, track visited node addresses, abort on cycle/invalid pointer/short read/PID change/exit.
- Timestamp before first memory read and after final read. If attached through any reviewed fallback, detach/resume immediately and report each detach status.
- Initial iPhone state is disconnected. No iPhone connection for this first pass.

## Compact output contract

Emit text or JSON containing only:

```text
READ_START_TIME
READ_END_TIME
JMCS_PID
JMCS_LOAD_BASE
MC_DEVS_PTR
MANAGER_PTR
REGISTRY_HEAD
SNAPSHOT_CONSISTENCY
DETACH_STATUS
ENTRY index: address, next, interface, context (= interface), slot0, slot4
```

No raw surrounding bytes, broad heap dump, callback invocation, score, or unrelated trace. Preserve traversal index exactly. The reader ends immediately after output.

## Offline callback resolution

For each pointer, on the Mac:

1. Parse the same-session maps snapshot and identify which mapped ELF range contains the runtime address.
2. Derive module load bias from mapping start, file offset, and ELF `PT_LOAD` segment (do not assume every module uses `runtime_base + address` without checking segment offsets).
3. Convert to ELF virtual address and normalize ARM/Thumb function-pointer bit (`address & ~1` for symbol lookup while retaining original pointer).
4. Resolve exact function/symbol/DWARF location from the saved `jmcs` ELF or the mapped shared object.
5. Analyze slot `+0` against the literal bytes for `"CarPlay Screen"`, including proven context fields. Calculate callback result only if control/dataflow is deterministic from this snapshot and static state.
6. Rank by unsigned score, strict greater-than, with earliest traversal ordinal winning ties. Initial best is zero.

Do not infer a callback's score from its name or nearby string. If resolution lands outside available ELF files, or behavior reads mutable state not in the snapshot, mark result unresolved and identify precisely which value is missing. Match-score capture remains `NO` unless this static process fails for a concrete runtime dependency.

## Conditional second stage

Only after the offline analysis, if at least one possible winning callback requires an unavailable live value, prepare a separately approved observation scoped to one ordinary `mc_dev_attach("CarPlay Screen", ...)`. Capture only `(entry identity, slot0 callback, returned unsigned score)` for candidates visited during that call. No stack/register dumps, unrelated breakpoints, broad tracing, or attach callback execution tracing. Do not perform this stage unless static analysis demonstrates the dependency and a new bounded design is reviewed.

## Safety aborts and recovery

Abort on PID/base mismatch, null global, pointer outside readable ranges, target exit, short read, cycle, >128 nodes, or denied attach/read. At most one clean retry after fixing a non-invasive operator/tool mistake. Never repeat stop/attach attempts to overcome permission denial; never restart `jmcs`.

## Reader implementation status (Step 22)

Source and offline procedure: [runtime-registry-reader.md](runtime-registry-reader.md). Synthetic tests pass. Maximum is 10,272 requested bytes if both permitted consistency attempts each need two passes (5,136 in the normal single-attempt case). No target memory writes or pauses are implemented. This Mac has no Android ARMv7 sysroot, so target build and syscall ABI remain unverified; target kernel support remains unknown. Do not execute until the ARMv7 binary is built and reviewed.

## Readiness

`READY TO PERFORM BOUNDED LIVE READ: NO`. Remaining pre-execution work: build with a verified Android ARMv7 toolchain/sysroot, inspect the target binary's imports, then separately approve a parked-session read. The design requires a parked car for execution, but not for this design work.
