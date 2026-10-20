# R7C2 Android fault matrix

| Fault | Evidence | Scope | Cleanup / state | Remaining gap |
|---|---|---|---|---|
| Null JNI Surface | Actual Dalvik | JNI boundary | Rejected; no owner created | None for null case |
| Invalid/stale/double lifecycle handle | Actual Dalvik, 100 cycles | Handle/receiver | Rejected; counters zero | Handle-ID exhaustion is host-only |
| Wrong generation / wrong stream | Actual Dalvik, 100 cycles | Stream-local request validation | Rejected; valid streams continue | None for these checks |
| Type111 Surface invalidated | Actual Dalvik JNI/native | Secondary stream | Type111 closes; Type110 remains active; zero after disconnect | Framework callback race not injected |
| Type110 Surface invalidated | Actual Dalvik JNI/native | Session-global | Both streams close | None for tested invalidation |
| Display enumeration / Presentation | Actual API17 Dalvik synthetic overlay | Display candidate | States recorded; Presentation dismissed on cleanup | Framework exception injection and Honda admission unknown |
| Audio open/write/lifecycle | Actual API17 AudioTrack when available | Audio adapter | Closed/double-close safe | Construction/write exception and stop-during-write not injected |
| Input allowlist / stale generation | Actual Java runtime | Input bridge | Unknown key and stale generation rejected | Callback registration race not injected |
| USB manager / no device | Actual API17 runtime | USB boundary | Empty discovery then close | Permission/endpoint callbacks simulated or absent |
| Production auth/iAP2/media defaults | Actual Java runtime | Security/session gate | Fail closed; explicit LAB only | Real providers remain unavailable |
| Java loopback | Actual API17 runtime | Java socket | bounded loopback closes | Native POSIX socket JNI runtime path not exercised |
| Native socket bounds/concurrency | Host ASan/UBSan/TSan | POSIX adapter | Pass | Android Bionic runtime interaction untested |
| Stop during setup/decode/audio/socket callback | Host model or not injected | Lifecycle | Partial | Deterministic Android barrier matrix remains open |
| Pending Java exception / lookup failure | Not injected | JNI | Bridge preserves/checks pending exception by code review | VM injection remains open |

R7C software-level matrix is therefore materially advanced but not closed. Honda-only warning, safe-area, real authentication/framing, USB ownership, audio/control equivalence, and restoration rows remain `EVIDENCE_REQUIRED` independently of these software gaps.
