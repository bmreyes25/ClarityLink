# Cumulative Mac receiver readiness matrix

Status reflects evidence on R6F starting head and this R6F review; no physical authority was connected and no real iPhone session was attempted.

| Area | Status | Evidence / blocker |
|---|---|---|
| authentication authority | ACQUISITION_REQUIRED | Select CPC200-CCPA + LIVI/LIVI Link; not present/proven |
| iAP2 | BLOCKED | LIVI stack candidate; not integrated |
| CarPlay activation | BLOCKED | Requires real authority and stack integration |
| authenticated control session | BLOCKED | No documented ClarityLink handoff; adapter needed |
| `/info` | INTERFACE_COMPLETE | Host builder exists; real required-field evidence missing |
| SETUP | HOST_CONFIRMED | Synthetic host code only; no real observation |
| Type110 negotiation | HOST_CONFIRMED | Synthetic model only |
| Type111 negotiation | HOST_CONFIRMED | Synthetic model only |
| Type110 security | PARTIAL | Host security scaffolding; no real validation |
| Type111 security | BLOCKED | Evidence-gated |
| Type110 listener | HOST_CONFIRMED | Host listener implementation, no real phone path |
| Type111 listener | HOST_CONFIRMED | Host listener implementation, no real phone path |
| Type110 media | HOST_CONFIRMED | Synthetic decoder path only |
| Type111 media | BLOCKED | Real encrypted stream absent |
| H264 decode | HOST_CONFIRMED | Synthetic H.264 decoded in Mac lab |
| primary Mac display | PARTIAL | Host synthetic display path |
| secondary Mac display | PARTIAL | Host synthetic display path |
| audio | PARTIAL | Capability interface; real `/info` values/negotiation unknown |
| controls | PARTIAL | Host input/control scaffolding; real path absent |
| teardown | HOST_CONFIRMED | Synthetic lifecycle/cleanup tests |
| reconnect | HOST_CONFIRMED | Synthetic generations only |
