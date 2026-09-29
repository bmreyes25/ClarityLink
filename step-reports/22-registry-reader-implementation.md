# Step 22 — bounded runtime registry reader implementation

Date: 2026-09-29

## Scope

Implemented the one-shot ARMv7-oriented reader and offline resolver. Development and offline review only: no vehicle, ADB, jmcs, iPhone, process-memory read, or target binary execution occurred.

## Results

- Reader source, build instructions, synthetic backend, and safety target: `research/tools/jmcs_registry_reader/`.
- Offline callback map/ELF resolver: `research/tools/resolve_runtime_registry.py`.
- Synthetic coverage passes empty/one/multiple and ordered registrations, 128/129 boundary, null manager, invalid head/interface, self/multi-node cycles, inconsistent snapshots, short read, EPERM, ENOSYS, and ESRCH.
- `make safety` found no forbidden imports in the synthetic binary. Source contains no target writes, ptrace, signals, pause/suspension, debuggerd, callbacks, or target memory file path.
- Two passes per attempt; at most two attempts. Successful normal attempt requests at most 5,136 bytes. Maximum across all attempts is 10,272 bytes.
- Static cell VA is `0x35acbc`; every future run must derive a new load bias, PID, and cell from current maps and matching ELF.

## Go/no-go

| Gate | Result |
|---|---|
| Reader implemented | Yes |
| ARMv7 build | Fail/unverified: no Android ARMv7 compiler/sysroot; compile attempt lacked target headers |
| process_vm_readv ABI | Unverified in this environment; build refuses to invent a syscall number |
| Target support | Unknown; likely 3.1-era kernel may lack the syscall unless backported |
| Target writes / process pause | None / none |
| Consistency | Immediate full second walk; one extra attempt maximum; otherwise discard |
| Synthetic tests | Pass |
| Ready for vehicle execution | No |

Precise blocker: produce and statically audit an ARMv7 Android binary using verified target-toolchain headers/sysroot that define `process_vm_readv`.

See [reader review and future parked procedure](../research/carplay/runtime-registry-reader.md). The car remains untouched.
