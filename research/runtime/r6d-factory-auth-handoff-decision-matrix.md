# R6D factory handoff decision matrix

`REUSE_NOT_SUPPORTED_BY_FOUND_BOUNDARY` is a bounded interface verdict, not a claim that all conceivable private integration is impossible. [Call graph](r6d-authenticated-session-transition-callgraph.md), [boundary audit](r6d-authenticated-session-boundary-audit.md), and [ownership](r6d-auth-session-object-ownership.md) contain the evidence.

| Layer | Factory owner / object | External boundary? / process local? | Transfer supported? / custom receiver use | Verdict / blocker |
|---|---|---|---|---|
| USB | `jmcs` USB host device | no identified API / local | no / receiver needs own transport | REUSE_UNPROVEN; fd/lifecycle |
| iAP2 | `jmcs` iAP device/owner context | no / local | no / own iAP2 or proven future adapter | REUSE_NOT_SUPPORTED_BY_FOUND_BOUNDARY |
| MFi/auth | `jmcs` auth callbacks and configured hardware | proxy in process only | no auth-session handoff / lawful own authority | REUSE_POSSIBLE_IN_PROCESS, not external |
| CarPlay attach | generic device probe → `mc_carplay_attached` | internal callback | no / own attachment state | REUSE_NOT_SUPPORTED_BY_FOUND_BOUNDARY |
| AirPlay receiver | `_AirPlayThread` server | internal CF object | no / custom receiver must own it | REIMPLEMENT |
| control transport | AirTunes connection | internal socket/handler | no / R6B contract needs independent producer | REIMPLEMENT |
| security context | connection SAP + receiver session | local opaque objects | no / own lawful negotiated context | REIMPLEMENT; no key access |
| `/info` | `jmcs` internal handler | internal | no / R6B emitter | REIMPLEMENT |
| SETUP | `jmcs` session handler | internal | no / R6A transaction | REIMPLEMENT |
| screen security | `jmcs` session/screen | internal | no / Type110 known, Type111 unknown | REIMPLEMENT with evidence gate |
| audio | `jmcs`/Android audio | stock callback API, local | independent route unproven | EVIDENCE_REQUIRED |
| controls | `jmcs`/iAP/HID | UI/state Binder only | native event reuse unproven | EVIDENCE_REQUIRED |

The reviewed factory stack offers no supported **external** authenticated-session transfer. An in-process replacement-process design might eventually reuse the installed authentication device through a legitimate, separately reviewed platform contract, but the current symbols do not establish that contract or authorize hardware access.
