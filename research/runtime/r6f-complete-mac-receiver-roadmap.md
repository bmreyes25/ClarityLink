# R6F–R6J complete Mac receiver roadmap

Architecture: one custom receiver, one authenticated iPhone session, Type110 to primary output and Type111 to secondary navigation output. Honda work starts only after R6J proof.

| Stage | Exit criteria |
|---|---|
| R6F — authority | Select/acquire a lawful genuine authority and a documented complete session stack; integrate the control handoff or produce exact acquisition specification. No synthetic progress.
| R6G — real control | One continuous authenticated iPhone session; real `/info` request reaches ClarityLink, response sent and accepted; next control request observed.
| R6H — real setup and descriptors | Real SETUP accepted; Type110 and Type111 negotiated in the same session; bind stream IDs and listeners.
| R6I — Type111 security/media/decode | Establish lawful Type111 security, receive bounded real media, decode real H.264, render secondary output.
| R6J — complete Mac dual-screen receiver | One real iPhone session AND real Type110 primary Mac output AND real Type111 secondary Mac output, with authentication/session ownership, teardown, reconnect, zero stale resources, and preserved audio/control architecture.
| R6K+ — Honda port | Begin only after R6J definition is met and separate project authorization/evidence review approves a Honda port. No Honda activity in R6F–R6J.

R6G consumes R6F's actual authority boundary. R6H consumes real `/info` and SETUP evidence. R6I consumes Type111 negotiation and security evidence. R6J is the Mac receiver proof gate; synthetic streams never satisfy a real gate.
