# R7E5F — Self-contained Test A process-bound closure

**Starting head:** `59f6a5f42dbf07b208410c38f959e34ba3a17ecc`  
**Implementation head:** `54e13e50ec0b65eb6e476db6760bcee351a6c479`  
**Decision:** `R7E_TEST_A_PROCESS_ROLLBACK_BLOCKED` — API17 x86 emulator runtime proof remains unobserved.  
**Next:** `API17_X86_RUNTIME_WATCHDOG_PROOF_REQUIRED`; Test A remains not authorized.

A0 is complete. A0-WR reviewed result remains `A0WR_PASS_FOR_REVIEW`; transfer and write/verify/delete are closed; no additional marker test is required. R7E5E's lack of Honda `ps` grammar/toolbox proof and the external ps-to-kill race remain historical facts. The new supervisor uses a direct `fork()` child PID, child and parent alarms, exact-child `waitpid`, and exact-child `kill` only in exceptional parent timeout handling. ECC reviewed the PID ownership and reaping race boundary. External toolbox `ps` and `kill` are not part of the proposed normal Test A commands.

Host fault tests passed: 7 focused tests, including version/self-test success, child loop and sleep deadlines, parent deadline, crash mapping, five repeated timeouts, and 100 successful version lifecycles. Child timeout returns 124; parent timeout returns 125; child signal crash maps to 126. API17 x86 runtime tests were not run because they require ADB, forbidden by this milestone. No Honda commands, writes, launches, or ADB commands occurred.

The rebuilt ARMv7 artifact is 7,228 bytes, SHA-256 `ea1cbd38e0b5a2162ab58b20c9f2758bcf25693106db2337897db8bf62ae256a`, MD5 `df4ff8b0de7b117cfee3be9c40ae452b`; ELF32 little-endian ARM EABI5 PIE. `DT_NEEDED`: `libdl.so`, `libc.so`. Imports match the pinned NDK r23c API17 ARM stubs; unknown imports: none. The ignored staging copy is byte-identical, mode 0555, and predicts remote mode 0555. These are build/static/host findings, not API17 emulator or Honda runtime proof.

No Test A collector, execution manifest, or authorization packet was created because the runtime gate remains open. No retry, fallback, external process discovery/kill, or automatic Test B is allowed. A host timeout beyond the future internal-bound-plus-grace threshold is `TEST_A_WATCHDOG_OR_TRANSPORT_ANOMALY`; stop target activity, preserve evidence, and require separate recovery review.
