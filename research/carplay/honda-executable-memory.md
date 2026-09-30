# Executable memory and cache synchronization — Step 40B

## What is established

The offline patch model changes bytes in a Python bytearray only. Unicorn maps synthetic code as emulator memory; that is not a target OS mapping or permission transition. The pinned `jmcs` ELF and its disassembly do not establish a supported runtime allocator for a nearby executable veneer, writable-code policy, thread suspension mechanism, or cache-maintenance API contract.

## Unknowns blocking a live hook

- Where a veneer page can be allocated within `BL` reach without modifying Honda text.
- Whether the target platform permits a safe W^X transition for the relevant page and how to restore the original permissions on every failure path.
- How all threads that could execute either call site are coordinated during replacement and restoration.
- Which platform-supported data/instruction cache synchronization operation makes written instructions visible to all relevant cores, including its required address range and barriers.
- How original page protections and veneer allocation are verified/released after restoration.
- What recovery remains possible if protection restoration, cache synchronization, verification, or process identity checks fail.

No permanent RWX assumption is made. No executable-memory API is called by this project code. `ICACHE SYNC MODEL: UNKNOWN`; `MEMORY PROTECTION MODEL: NOT READY`. Step 41 stays blocked until these are independently grounded in target-platform evidence and tested in an appropriate isolated environment.
