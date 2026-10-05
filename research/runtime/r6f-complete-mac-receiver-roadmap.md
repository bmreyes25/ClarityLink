# R6F–R6J complete Mac receiver roadmap

Architecture: one custom receiver, one authenticated iPhone session, Type110 to primary output and Type111 to secondary navigation output. Honda work starts only after R6J proof.

| Stage | Exit criteria |
|---|---|
| R6F — authority | Select/acquire a lawful genuine authority and a documented complete session stack; integrate the control handoff or produce exact acquisition specification. No synthetic progress.
| R6G — LIVI control handoff + real `/info` | First complete and test the small LIVI pre-dispatch control delegate/bridge; then one continuous authenticated iPhone session reaches ClarityLink, real `/info` is sent and accepted, and the next control request is observed. R6G found the source seam but did not complete the LIVI bridge; adapter completion is the current prerequisite.
| R6H — real setup and descriptors | Real SETUP accepted; Type110 and Type111 negotiated in the same session; bind stream IDs and listeners.
| R6I — Type111 security/media/decode | Establish lawful Type111 security, receive bounded real media, decode real H.264, render secondary output.
| R6J — complete Mac dual-screen receiver | One real iPhone session AND real Type110 primary Mac output AND real Type111 secondary Mac output, with authentication/session ownership, teardown, reconnect, zero stale resources, and preserved audio/control architecture.
| R6K+ — Honda port | Begin only after R6J definition is met and separate project authorization/evidence review approves a Honda port. No Honda activity in R6F–R6J.

R6G consumes R6F's actual authority boundary. Current R6G source audit found the exact LIVI control seam; next R6H action is to complete the small upstream delegate and bridge, then use the hardware for authority bring-up and real `/info`. R6I consumes Type111 negotiation and security evidence. R6J is the Mac receiver proof gate; synthetic streams never satisfy a real gate.
