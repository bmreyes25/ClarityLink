# Honda integration contract gaps

This is the CL-IF-01 input checklist. The source-pinned CL-R9 and CL-R10 documents are the current public evidence base; this table does not claim exhaustive inspection of every Honda software revision.

| Boundary | Known evidence | Missing contract | Gate result |
|---|---|---|---|
| Receiver `/info` | Inspected path describes main display; public report scopes exact source/artifacts. | Authorized second-display advertisement, descriptor semantics and versioned feature set. | `RECEIVER_AUTHORIZED_SPEC_REQUIRED` |
| Control SETUP | Inspected Honda path does not establish Type111 accepted-feature ownership or dispatch. | Proposal/response schema, success/error behavior, same-session ownership and rollback. | NO-GO |
| Stream transport | Synthetic Type111 pipeline exists; separate PlayPort observation exists. | Honda authenticated Type111 session context, identity, transport readiness, config, revocation and independent teardown. | NO-GO |
| Display sink | Honda ownership evidence exists; no supported arbitrary-frame admission established. | Authorized caller, accepted source/format, physical Navigation bounds, page selection, warnings, generations, host restart and restore. | `DISPLAY_SUPPORTED_PATH_NOT_FOUND` |
| Safety | Lab warning priority and cleanup have API17 evidence. | Independent review of target hazards, no-mask guarantee, vehicle-bus boundary, rollback and stop conditions. | NOT REVIEWED FOR TARGET |

## Decision rule

Evidence must be versioned and authorized, include complete ownership and lifecycle fields, and be independently reviewed. A private function, Xposed hook, Binder method, display layer, symbol, or analogous Audi implementation cannot fill a missing supported contract. If either receiver or display contract remains ambiguous or unsupported, CL-IF-01 records NO-GO. Preserve `safeForHonda() == false`.
