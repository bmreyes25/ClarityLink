# R7C7 production Android socket fault matrix

All fault cases below ran through the production `AndroidSocketAdapter` on the owned API 17 Dalvik emulator. For Type111-local faults, the harness verifies Type110 can subsequently send a valid frame and post it; the faulting stream closes and its descriptors return to zero.

| Fault | Scope / result |
|---|---|
| Timeout | Type111 local; Type110 follow-up passes; FD zero |
| Peer close | Type111 local; Type110 follow-up passes; FD zero |
| Malformed frame | Type111 local; Type110 follow-up passes; FD zero |
| Truncated header | Type111 local; Type110 follow-up passes; FD zero |
| Truncated payload | Type111 local; Type110 follow-up passes; FD zero |
| Zero payload | Type111 local; Type110 follow-up passes; FD zero |
| Oversized declared payload | Type111 local; rejected before payload allocation; Type110 follow-up passes; FD zero |
| Wrong stream | Type111 local; Type110 follow-up passes; FD zero |
| Wrong generation | Type111 local; Type110 follow-up passes; FD zero |
| Type111 connect refusal | Type111 local; Type110 follow-up passes |
| Type110 connect refusal | session-global shutdown |
| Local port collision | NOT_APPLICABLE: adapter is client-only and binds an ephemeral local port; it has no configured listener bind operation |
| Read shutdown | checkpointed active read interrupted and worker joined |
| Write shutdown | checkpointed active write interrupted and worker joined |

The oversized case is specifically an over-limit declared length, not a separate oversized body transfer. Combined matrix event: `NATIVE_SOCKET_FAULT_MATRIX=PASS`.
