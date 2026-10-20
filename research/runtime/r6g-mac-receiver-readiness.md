# R6G Mac receiver readiness

| Capability | Status | Evidence |
|---|---|---|
| CPC200 hardware | HARDWARE_REQUIRED | No candidate product detected in safe USB inventory |
| LIVI Link provisioned | NOT_STARTED | No compatible unit |
| Genuine MFi confirmed | NOT_STARTED | No coprocessor present or tested |
| LIVI upstream authentication | NOT_STARTED | No phone/hardware attempt |
| LIVI control seam | PARTIAL | Pre-dispatch `CpStack.attachSocket` seam identified; small upstream patch required |
| ClarityLink LIVI provider | ADAPTER_COMPLETE | `auth_providers/livi.py` implements existing boundary; no real LIVI bridge implementation yet |
| Authenticated handoff | HOST_CONFIRMED | Existing R6E one-shot handoff applies; synthetic provider tests only |
| Real control transport | PARTIAL | Adapter class is complete against proposed bridge contract; bridge absent |
| `/info` received | NOT_STARTED | No real session |
| `/info` sent | NOT_STARTED | No real session |
| `/info` accepted | NOT_STARTED | No real session |
| SETUP | NOT_STARTED | No real session |
| Type110 | NOT_STARTED | No real session |
| Type111 | NOT_STARTED | No real session |
| Type111 listener | NOT_STARTED | Existing offline models only |
| Type111 security | NOT_STARTED | No real session |
| Type111 media | NOT_STARTED | No real session |
| H.264 decode | HOST_CONFIRMED | Offline host tests from prior milestones; not real Type111 |
| Primary output | NOT_STARTED | No live stream |
| Secondary output | NOT_STARTED | No live stream |
| Audio | NOT_STARTED | No live session |
| Controls | NOT_STARTED | No live session |
| Teardown | HOST_CONFIRMED | Existing host lifecycle; LIVI bridge disconnect untested live |
| Reconnect | PARTIAL | Synthetic lifecycle loops only; no device/session reconnect |

Synthetic tests establish no R6G real-iPhone tier. Highest tier remains `BELOW_R6G_T0`.
