# Honda hook safety contract (Step 39)

This milestone implements only data models: `ExpectedFunctionIdentity`, `HondaBinaryIdentity`, `HookGroupGate`, and `FailClosedHookPolicy`. They compare an externally supplied exact binary identity and exact function prologue byte strings; they do not read executable memory, discover prologues, patch code, or install hooks.

Policy requires the full server-info, Setup, SessionStart, and teardown hook group. Missing any member disables the group. Capability advertisement must not be enabled without Setup, and persistent Type111 state must not be created without lifecycle support. Exact Honda prologue bytes, calling conventions, CF ownership, and safe trampoline points are intentionally not fabricated; see `honda-hook-abi.md`.
