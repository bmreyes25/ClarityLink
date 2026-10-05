# R6D factory oracle readiness

| Element | Status | Evidence / limit |
|---|---|---|
| Factory IC channel | CONFIRMED_STATIC | configured `/dev/i2c-2`; device runtime not observed |
| Address semantics | CONFIRMED_STATIC | `0x10` passed unshifted to Linux `I2C_SLAVE` |
| Protocol/version | PARTIAL | `get_auth_level` exists; semantic correspondence unknown |
| Certificate operation | CONFIRMED_STATIC | AirPlay and iAP2 paths |
| Challenge/signature | CONFIRMED_STATIC | AirPlay and iAP2 paths |
| Status | CONFIRMED_STATIC | readiness poll/read |
| Reset | PARTIAL | symbol exists; side effect unresolved |
| Lifecycle/locking | PARTIAL | single `jmcs` fd and mutex; cross-process unknown |
| iAP2 use | CONFIRMED_STATIC | `auth_thread` path |
| AirPlay use | CONFIRMED_STATIC | `APSMFiSAP_Exchange` path |
| Clean-room ABI | MODEL_COMPLETE | Python protocol only; native API17 header not built |
| Synthetic oracle | MODEL_COMPLETE | host-only fake bytes |
| iAP2 auth orchestration | PARTIAL | generic state choreography; no wire protocol |
| AirPlay auth orchestration | PARTIAL | shared primitive proven, wire/crypto integration absent |
| Real Honda oracle | NOT_AUTHORIZED | no live I²C code |
| Real iPhone | BLOCKED | no lawful Mac lab oracle/session connected |
| Type110 / Type111 | PARTIAL | host receiver model; no real iPhone session |

Highest ClarityLink receiver level remains host synthetic R6-L1. `ARCH_D_FULL_CLARITYLINK_RECEIVER_WITH_FACTORY_AUTH_ORACLE` is the selected *implementation architecture*, not a completed integration.
