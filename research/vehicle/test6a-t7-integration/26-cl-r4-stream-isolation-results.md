# CL-R4 stream isolation — historical summary

**Reported disposition:** `PARTIAL` in the prior engineering campaign. Raw emulator receipts and screenshots are excluded from this public candidate; detailed local evidence remains in the engineering checkout.

The reported API17 Binder v3 contract carries session, stream type, connection, stream generation, output, and frame sequence identities. Type110 and Type111 are routed to distinct laboratory sinks. The reported implementation bounds Type111 dispatch, rejects stale generations and unsupported older descriptors, and uses reject-new behavior for already decoded frames. The recorded saturation scenario reported Type110 progress while Type111 output was blocked, no cross-routing, and zero transfer/retained-byte counters at teardown.

The same campaign reported H.264 fixture decoding, View rendering, pixel checks, and a negative control. It also documented an incomplete uncaught-crash rerun with an unattributed `FinalizerWatchdogDaemon` timeout; that failure is not hidden by the earlier crash-dialog result.

CL-R4 remains partial. The remaining API17 fault/reconnect acceptance includes independent sink reconnection, Type110-only ownership, parent-authority process death, and reentrant teardown. These laboratory models do not establish Honda Type110 behavior, authenticated Honda Type111, factory warning priority, or physical display scanout. `safeForHonda()` remains false.
