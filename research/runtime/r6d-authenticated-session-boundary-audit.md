# R6D exact supported-boundary audit

Scope is the two hash-matched preserved ELF files and R3C/R6C static service inventories. An exported symbol is a linker fact, not a supported consumer contract.

| Surface checked | Evidence | Classification |
|---|---|---|
| `jmcs` ELF symbols | `ios_iap2_set_authenticated`, `AirPlayReceiverServerCreate`, `AirPlayReceiverSessionCreate` reside in executable; no separate ABI/version/consumer is evidenced | INTERNAL_FUNCTION or EXPORTED_SYMBOL, not supported external API |
| `libcarplay_proxy.so` dynamic exports | auth/audio/screen forwarding and singleton registrations; no AirPlay session creation, request read/write, or security export | SHARED_LIBRARY_API for stock process, PROCESS_LOCAL_ONLY |
| callback structures | 28-byte AirPlay server delegate and auth/audio/screen proxy records point to process-local callbacks; screen/auth registration is singular | INTERNAL_CALLBACK |
| Binder and Android services | `CarPlayApService` exposes UI/state/call/navigation/Siri categories; reviewed interface carries no iAP2 handle, control request, session FD, or screen context | SUPPORTED_IPC for UI only; not auth handoff |
| local/Unix sockets, fd passing, shared memory | `jmcs` imports `socketpair` and `recvmsg`, so mere socket presence cannot be excluded. Visible `recvmsg` call sites are generic `SocketRecvFrom` (`0x2a0836`) and DNS `getResultList` (`0x2a59ce`), not an identified auth-session bridge. No `SCM_RIGHTS` handling or named authenticated-session channel was recovered | UNKNOWN for other generic paths; no supported handoff found |
| JNI/service manager/message queues | reviewed native and app-service boundaries have no structured CarPlay session transfer | no supported handoff found in reviewed surfaces |
| plugin/dynamic loader | `dlopen/dlsym` sites reviewed in [R3C](jmcs-dlopen-sites.md) are generic/SQLite; no CarPlay plugin lookup is evidenced | no supported receiver plugin |
| documented Honda factory API | no publication or project-preserved declaration of an authentication-to-receiver handoff | UNKNOWN outside preserved image |

**Bounded result: `R6D_NO_SUPPORTED_FACTORY_SESSION_HANDOFF`.** This means the audited artifacts do not offer a supported external handoff with ownership, request/response, security and close semantics. It is not a universal claim that a future Honda API cannot exist. The remaining theoretical possibilities do not justify keeping the factory-handoff architecture as the primary engineering plan.
