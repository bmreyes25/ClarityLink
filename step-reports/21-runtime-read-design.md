# Step 21 — minimum runtime registry read design

Date: 2026-09-29

## Scope

Design a bounded read-only observation of the `mc_devs` registry. Documentation only: no vehicle, ADB, iPhone, debugger, process-memory access, or live execution was used.

## Findings

- `mc_devs` is a pointer cell at ELF VA `0x35acbc`; previous runtime base `0x4008f000` placed it at `0x403e9cbc`. Future execution must rediscover PID and base.
- `dev_attach` starts its list walk at manager `+0x08`. Registry nodes are allocated as `0x0c` bytes; `+0x00` is next and `+0x08` is interface. Candidate callback words are interface `+0x00` (ranking/match) and `+0x04` (attach).
- Complete manager size is unknown. Manager `+0x0c` maintains the append tail-link; `+0x10` is also accessed but is not needed to locate the list.
- Saved ARM disassembly shows node `+0x04` stores prior incoming-link location, not candidate context. The callback receives the interface pointer as its second/context argument. Registration appends at tail; list traversal is chronological registration order and is the tie order.
- Initial collection should not call `mc_dev_attach` or capture scores. Resolve pointers and evaluate slot `+0` statically against `"CarPlay Screen"` first. Live score capture is conditional on demonstrated dependence on unavailable mutable state.
- `process_vm_readv` is the preferred first method if supported/permitted; support on this Android target is unknown. The Step 22 implementation has no automatic ptrace fallback. Unsupported or denied reads stop. No debugger server, injection, patch, target write, restart, or tombstone is allowed.
- iPhone remains disconnected for the first observation. Candidate presence in that state is still unknown.

## Decision gate

| Item | Result |
|---|---|
| Live memory byte bound | `8 + 20N` bytes (<=2,568 at 128 entries), pending field confirmation |
| Pointer chain | Global cell -> manager -> manager `+0x08` -> node `+0x00/+0x08` -> interface `+0x00/+0x04`; callback context aliases interface |
| Match-score capture | Only if offline callback evaluation cannot reproduce a score because of an unavailable runtime dependency |
| Target writes | None |
| Car needed for design / execution | No / Yes, parked |
| Ready to execute | No; review a one-shot reader and target permissions |
| Biggest risk | Inconsistent list snapshot or failure to resume every stopped thread under ptrace |

## Deliverables

- [Runtime read plan](../research/carplay/runtime-registry-read-plan.md)
- [Runtime layout](../research/carplay/runtime-registry-layout.md)
- [Runtime registry evidence/status](../research/carplay/runtime-device-registry.md)

The reader source and offline review are in [Step 22](../../step-reports/22-registry-reader-implementation.md). ARMv7 target build and target syscall permission/support remain unverified; do not execute on the car until separately reviewed.
