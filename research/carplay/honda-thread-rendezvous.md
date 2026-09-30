# Step 40C — thread rendezvous gate

## Findings

Patching a four-byte Thumb `BL` is unsafe while any thread can execute it. Honda's Setup callsite is `0x28af72`, only 2-byte aligned: the two halfwords cross a 4-byte boundary. There is no established single atomic store for the complete instruction. A thread may fetch the old instruction, the new instruction, or a mixed pair while a write is in progress. Cache synchronization does not provide mutual exclusion.

The API-17 Bionic syscall table includes `futex`; this alone is not a process-wide stop-the-world API. Signal-based parking is not established as safe: signal masks, application handlers, handler reentrancy, thread exit/creation during enumeration, signal ownership, acknowledgements/timeouts, and each parked thread's saved PC need a defined protocol. This project has no validated way to enumerate a stable set and inspect saved program counters without using a debugger interface (excluded here). A signal rendezvous implemented only for cooperative threads could not prove that arbitrary Honda threads reached the checkpoint.

Process-start installation would only avoid active callers if installation is guaranteed before worker creation and before the target callsites can run. No such injection/startup contract is established. External suspension is out of scope. Restoration has the same rendezvous requirement and additionally must wait until no thread is inside or can return through a veneer before freeing it.

## Decision

`UNCOORDINATED PATCH: UNSAFE`

`THREAD RENDEZVOUS: NOT READY`

The host model `rendezvous_model.py` rejects an incomplete parked set, thread-generation changes, and saved PCs within patch/veneer ranges; a separate lifetime predicate prevents modeled veneer release before restoration and zero in-flight callers. This only checks supplied synthetic facts—it cannot acquire them from a running process or guarantee thread creation is blocked.

Required future evidence: a platform-supported mechanism that blocks thread creation, safely parks every relevant thread, obtains/validates saved PCs outside the patch/veneer pages, detects timeout/exit, and resumes only after protections and cache state are verified. No real signal was sent and no target thread was inspected.

## Step 40D status

The official API-17 ARM image was obtained, but no ARM guest could be booted by the available Apple Silicon emulator; therefore signal-context layout, futex behavior, task enumeration, saved-PC parsing, and rendezvous stress remain **NOT AVAILABLE** in a real API-17 process. The maintained host safety-model tests do not close those runtime gaps. A read-only target preflight is now the appropriate next evidence step; it is not authorization to patch or execute a test helper on the vehicle.
