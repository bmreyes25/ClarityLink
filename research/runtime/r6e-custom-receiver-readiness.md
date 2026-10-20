# R6E custom receiver readiness

Highest real-iOS tier: `BELOW_R6E_T0`. Synthetic tests do not establish real-iOS behavior.

| Gate | Status | Evidence / blocker |
|---|---|---|
| authorized authentication authority | BLOCKED | genuine hardware/service absent |
| authentication provider | INTERFACE_COMPLETE | reviewed authority contract, selection fails closed |
| authenticated handoff | HOST_CONFIRMED | synthetic contract tests, generation/claim/close |
| control transport | INTERFACE_COMPLETE | structured channel adapter; no real wire adapter |
| stable identity | HOST_CONFIRMED | owner-only generated file outside Git; not created in this worktree |
| /info structure | PARTIAL | shape complete with injected capabilities; accepted values unknown |
| real authentication | BLOCKED | no authority |
| real /info request | BLOCKED | T0/T1 unavailable |
| real /info response | BLOCKED | T3 unavailable |
| iPhone acceptance | BLOCKED | no exchange |
| real SETUP | BLOCKED | no exchange |
| real Type110 | BLOCKED | no exchange |
| real Type111 | BLOCKED | no exchange |
| Type111 listener | HOST_CONFIRMED | host synthetic only |
| Type111 security | EVIDENCE_REQUIRED | real session context and Type111 KDF unknown |
| Type111 media | EVIDENCE_REQUIRED | real protected frames absent |
| H264 decode | HOST_CONFIRMED | synthetic sample only |
| HostWindowDisplay | HOST_CONFIRMED | synthetic host display only |
| Honda adapter | EVIDENCE_REQUIRED | R6D external handoff closed; no Honda work |

Decision: `R6E_AUTHORITY_NOT_AVAILABLE` / `R6E_AUTH_TRANSPORT_IMPLEMENTED_NOT_REAL_VALIDATED` / `R6E_REAL_IOS_NOT_REACHED`. Next: `GO_FOR_R6F_AUTHORITY_INTEGRATION`.
