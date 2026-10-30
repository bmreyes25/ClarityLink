# Remaining Type111 evidence blockers and next engineering actions

Root access alone does not establish a valid Type111 authentication or display contract. Existing evidence supports normal factory Type110 operation and static Type111 research only. The following evidence remains unproven for the Honda target:

| Blocker | Evidence needed | Least intrusive next action | Status |
|---|---|---|---|
| `/info` control flow | Exact receiver decision path, fields and supported capability advertisement | Continue offline source/native analysis; if ambiguity remains, use only reviewed bounded process metadata or a separately reviewed experiment | Unresolved |
| SETUP response | Actual accept/reject semantics, errors, negotiated parameters and ownership | Offline parser/call-graph analysis first; no synthetic request to Honda | Unresolved |
| Secondary display advertisement | Whether the same Honda parent session advertises a real secondary display | Static framework/receiver analysis; later correlate approved ordinary Type110 runtime observations | Unresolved |
| Type111 request conditions | Which capability, request and session preconditions trigger Type111 | Build a source-backed state/condition table; static strings or library dependencies do not prove runtime behavior | Unresolved |
| Parent session authority | Who owns authentication, keys, configuration, connection and child session | Trace binder/native/object ownership offline and compare saved authorized protocol evidence | Unresolved |
| Native transport identity | Exact socket, FD/inode, native library and process ownership | Use R2/R3 only after separate approval; correlate only exact FD/inode evidence | Unresolved; current global network evidence is not process attribution |
| Teardown and revocation | Order, trigger, authority and idempotence for disconnect, host death and session withdrawal | Complete offline state-machine and synthetic adversarial tests; later observe only under separate scope | Unresolved |
| Frame admission | Supported caller, authentication, format, bounds and failure behavior at Display 1 | Continue offline API-17/HondaHack host contract analysis; no direct display call | Unresolved |
| Display host View ownership | Whether HondaHack View remains owned by its host through Navigation and Stop Casting | Separate reviewed UI observation profile; static Xposed host analysis remains the prior evidence | Unresolved |
| Factory restoration and warning priority | Measured withdrawal, stock restoration and warning/instrument precedence | Independent display safety review and separate owner-authorized observation; do not generate warnings | Unresolved |

## Engineering sequence

1. Reconcile saved `jmcs` ELF dependencies with captured runtime mappings only if an approved root-read session becomes safe and authorized. Static NEEDED entries remain static facts; runtime loads need map evidence.
2. Use available authorized receiver evidence to finish an offline `/info`/SETUP control-flow matrix. Name each branch and its source evidence; retain `UNKNOWN` where the call path is not recovered.
3. Add synthetic contract tests for rejected Type111 SETUP, parent-session revocation, transport disconnect, process death, stale generation and frame admission bounds. Keep Type110 path isolated.
4. Analyze HondaHack ExternalDisplay host/View ownership offline. The UI-only casting observation is a separate future step and does not authorize instrumentation.
5. Produce a single traceable Type111 contract proposal with authentication/session authority, display advertisement, transport ownership, frame format/admission, teardown, warning priority and restoration. Require evidence for every target-specific assertion.
6. Do not propose active instrumentation or receiver modification until a specific question cannot be answered offline and a distinct qualified review plus demonstrated independent recovery plan exist.

No live Type111 request, active process attachment, injected code, receiver patch, or Honda modification is authorized by this record. `safeForHonda()` remains false.
