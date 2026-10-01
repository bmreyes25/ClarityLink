# `_requestSendPlistResponse` wrapper audit — Step 43M

Function: local Thumb function at `0x289f60`, size `0xb8`. It is called directly from four locations (`0x28a19c`, `0x28afba`, `0x28b42a`, `0x28b54e`) and is absent from `.dynsym`. Its ABI is `(HTTPConnectionRef, HTTPMessageRef, response CF object, OSStatus *statusOut)` in `r0-r3`.

At the Setup callsite, those arguments are the exact connection (`r4`), request/message (`r6`), mutable response (`[sp+0x54]`), and status slot (`[sp+0x50]`). The exact parsed Setup dictionary remains caller-local `[sp+0x1c]`, and the session pointer remains `[r10+0xf4]`. A connection-to-session chain is also statically confirmed in `_connectionFinalize`: connection `+8` → private context `+0xf4` → session. No guessed offset is used, though this chain does not provide the original parsed request dictionary.

The helper initializes response headers, synchronously calls `CFPropertyListCreateData` (`0x28e6fc`, format `0xc8`), extracts data pointer/length, and calls `HTTPMessageSetBody` (`0x29d01c`). It returns `0xc8` when serialization and body installation succeed, `0x1f4` on failure, and writes the body-set/error status through `statusOut`. The caller's success condition is `return == 0xc8 && *statusOut == 0`. It copies serialized bytes into HTTP message storage; caller later releases the response graph. This is local response readiness only.

### Wrapper contract

A project wrapper at the exact callsite can use the still-live caller frame to derive `(opaque session pointer, project generation)`, inspect request read-only, prepare resources, fully build a synthetic/project response entry, append it as the last local graph mutation, then call the original serializer exactly once. On result `0xc8` plus `statusOut==0`, it commits; otherwise it rolls back project-only resources and returns Honda's exact result/statusOut. On any project preparation/build failure it skips response mutation, rolls back, calls stock serializer once with the original Honda graph, and preserves stock Type110/audio. It uses no process-global current-session variable.

Wrapping the function entry instead is broader: four callers share it and the request dictionary/session generation are not explicit args. The connection can recover session identity through a proven chain, but transaction classification still requires examining request/message semantics. The exact callsite avoids this ambiguity and retains the Setup request dictionary on stack.

**Conclusion:** a stock-delegating transaction wrapper is a valid offline architecture, but the normal ELF call is internal/direct and cannot be interposed through the observed PLT/GOT. The future attachment is a one-callsite Thumb trampoline at `0x28afba`; runtime mechanism remains unknown. No Honda code was patched or run.
