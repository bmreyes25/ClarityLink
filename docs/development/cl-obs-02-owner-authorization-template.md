# CL-OBS-02 owner authorization template

**Blank template. Not signed, not approved, not an authorization.** Nothing in this repository or in any assistant output fills it in. The owner completes it privately, for the exact reviewed procedure. A copy with real names, signatures or vehicle identifiers is private and is never committed. `safeForHonda() == false`.

Without every field below completed by the people named, the status is `VEHICLE_SESSION_NOT_AUTHORIZED`.

| Field | Value (owner fills in) |
|---|---|
| Procedure | CL-OBS-02 [operator packet](cl-obs-02-operator-packet.md) and [preflight packet](cl-obs-02-preflight-packet.md) sections 3 to 6, plus PR #87 proposal at `fc4623f9e0b7798f9f3f335f2ca4d5d448bdc799` |
| PR #89 head SHA approved | |
| Independent safety review | Reviewer, date and SHA reviewed (from the [review packet](cl-obs-02-safety-review-packet.md) section 9) |
| Reviewer decisions | R-1 center display: ___  R-2 pre-recording Stop Casting: ___  R-3 camera mount: ___ |
| Vehicle and scope | One parked vehicle (described privately, no VIN here), one session, one transition sequence, existing casting feature only |
| Intended date of session | |
| Vehicle state (parked, parking brake, ignition state normally used) | |
| Agreed other factory page (reachable by the normal page control alone) | |
| Operator and recorder | Roles and names recorded privately |
| Equipment | Fixed camera, mount as approved in R-3, visible timer, optional rigid scale |
| Time limit | At most 10 minutes of recording, one session, no retry under this approval |
| Stop procedure | Operator and recorder have read the stop conditions and the stop/restoration steps in the operator packet |
| Restoration criteria | Casting off, factory Navigation visible as in the baseline, center display normal; otherwise end, no second attempt |
| Evidence storage | Private location (approved by the owner; outside every Git work tree): ___ |
| Exclusions | Everything in preflight section 9 |

## Acknowledgments (each initialed by the owner)

- [ ] This session is observational. It does not establish supported CarPlay integration, frame admission, OEM approval, warning priority, host crash recovery or a SafeArea.
- [ ] Casting and page selection are normal UI actions that change what the vehicle displays. This is not a no-operation test.
- [ ] A stop or abort ends this approval. A new session needs a new approval.
- [ ] Any edit to the approved documents after this date voids this approval.
- [ ] Raw media stays private; nothing is uploaded; only a de-identified text summary may be published after review.

## Operator confirmation (the operator, not the owner by proxy)

- [ ] I have read and understand the stop conditions and the stop procedure.

| Role | Name | Signature | Date |
|---|---|---|---|
| Owner | | | |
| Operator | | | |
| Independent qualified safety reviewer | | | |

After signing, record the three booleans in the private `observation.json` (`owner_written_approval`, `independent_safety_review`, `operator_read_stop_procedure`). Setting them without the signed approvals above is a false record.
