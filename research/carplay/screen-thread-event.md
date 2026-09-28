# Screen thread event trace

**Status: wait/start edge confirmed; producer unresolved.**

`_ScreenThread` (`jmcs`, VA `0x283dad`) reads its wait object from the screen-session context at `[r4 + 0x1400 + 0x18]` and calls helper `0x2a0480` at `0x283de4`, with timeout argument `10` and a local timing structure. When that call returns zero, the worker proceeds through session-state handling and invokes `AirPlayReceiverSessionScreen_StartSession` at `0x283eb6` (`0x2883a9`). A nonzero result takes an error/cleanup path.

The helper's implementation and synchronization primitive are not identified by the indexed excerpts. It is therefore **not proven** to be `sem_wait`, `pthread_cond_wait`, or another named primitive. The existing excerpt also does not show where the wait object is initialized/stored or which functions signal it.

| Question | Result |
|---|---|
| Wait function | Helper `0x2a0480`; primitive unknown |
| Wait object | `[r4 + 0x1400 + 0x18]` |
| Object creation/storage | Unknown; initializer/xrefs absent from focused excerpt |
| Signal/post callers | Unknown; signal producer/xrefs absent |
| State changed before wake | Unknown |
| Function that makes worker start a screen session | Successful return from helper `0x2a0480` in `_ScreenThread`; upstream producer unknown |

The exact next artifact needed is a caller/xref trace for helper `0x2a0480` and the object at session offset `+0x1418`, including initialization and every signal path in `jmcs`. No specific semaphore or condition-variable API is asserted.
