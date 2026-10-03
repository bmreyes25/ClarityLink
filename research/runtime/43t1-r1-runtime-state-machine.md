# 43T1-R1 runtime state machine

This document specifies a future design. The accompanying Python state model has no target-I/O backend and is not an implementation of an attachment or patcher.

| State | Entry condition | Exit condition | Abort condition | Rollback action | Allowed next states | Forbidden transitions |
|---|---|---|---|---|---|---|
| `UNATTACHED` | no target handle or project resources | approved identity and bounded procedure exist | any missing authorization/precondition | none | `ATTACH_PENDING`, `ABORTED` | directly to patched/prepared |
| `ATTACH_PENDING` | separately reviewed transport and identity checks begin | exact process/image/map and permitted attach method verified | mismatch, timeout, target ambiguity, unsupported permission | detach handle if known safe; otherwise unknown | `ATTACHED`, `ABORTED`, `UNKNOWN` | skip identity to prepared |
| `ATTACHED` | handle proven to refer to correct live process | quiescence/mapping/version evidence complete | handle stale, thread churn, process epoch changed | release handle without code writes | `PREPARED`, `ROLLBACK_PENDING`, `ABORTED` | patch without prepare |
| `PREPARED` | stock bytes/hash/address/alignment/decoded sequence/target captured; policy and resources validated | all resources staged, max-duration/write budget checked, target still same epoch | any pointer/CF/route/ABI evidence missing | clean project-owned staged resources | `PATCHED`, `ROLLBACK_PENDING`, `ABORTED` | listener or append before explicit request/contract |
| `PATCHED` | only bounded RAM patch action recorded in proposed plan | independent exact candidate-form readback and protections/cache completion observed | partial write, changed bytes, cache failure, timeout, host loss | compare exact expected project form, restore only if safe; else UNKNOWN | `VERIFYING`, `ROLLBACK_PENDING`, `UNKNOWN` | serializer/listener until install independently verified |
| `VERIFYING` | candidate state matches expected span and one transaction generation | all invariants and ownership contracts hold | any invariant failure | `ROLLBACK_PENDING` | `ROLLBACK_PENDING`, `ABORTED`, `UNKNOWN` | direct `DETACHED` |
| `ROLLBACK_PENDING` | any abort after possible write or resource creation | exact resources inventoried and rollback order selected | unexpected state, unknown project bytes, epoch change | stop Type111 work, retire exact generation, close owned FD/listener, stop worker/bridge, restore only known exact span | `RESTORING`, `UNKNOWN` | start another generation or retry serializer |
| `RESTORING` | rollback operations begun against exact generation and known state | independent exact address/hash/bytes/alignment/instruction/branch/resource readback passes twice; subsequent attempts idempotent | failed write/protection/cache/readback, interruption without fresh readback | no speculative writes; preserve diagnostic state | `VERIFIED`, `UNKNOWN` | claim success from write return alone |
| `VERIFIED` | independent verifier says exact stock state and all resources absent | detach handle and perform post-operation sanity | any new mutation, stale evidence, failed sanity | re-enter controlled rollback only if exact known project state; otherwise UNKNOWN | `DETACHED`, `UNKNOWN` | reattach or reuse stale facts |
| `DETACHED` | handle released and final evidence recorded | terminal | no transition | none | none | every state transition |
| `ABORTED` | abort before any possible target write; no resources remain | terminal | if write possibility is later discovered, promote to UNKNOWN | none or cleanup proven host-owned objects | none | PATCHED/VERIFIED |
| `UNKNOWN` | evidence insufficient or unexpected interruption/loss | terminal pending separately reviewed recovery | all unmodeled or uncertain state | do not guess; recovery must be independently designed | none | VERIFIED/DETACHED claims |

The executable model in `src/claritylink-honda/runtime_safety_model.py` checks legal state edges and fails incomplete postconditions closed. It does not encode every hardware or OS effect. The future checklist and failure matrix remain authoritative for preconditions and recovery boundaries.

## Required invariants at every transition

1. Type110's object graph and ownership are unchanged.
2. Stock serializer invocation count is exactly one after the response path begins.
3. Stock return/status and caller continuation are preserved.
4. No wildcard listener binding.
5. Each project object/socket/worker belongs to one transaction generation.
6. Stale generations cannot clean current-generation resources.
7. Every CF pointer is explicitly owned or borrowed; no guessed retain/release.
8. Listener and accepted connection have a single generation owner.
9. Pointers are validated before use; nullable outputs are checked before dereference.
10. Rollback and restoration are distinct facts; neither can be inferred from attach failure or process loss.

## Rollback ordering

Stop request/Type111 work → retire the exact generation → close accepted connection → close listener → stop/join worker → disable bridge → compare candidate patch bytes → restore only exact candidate bytes → synchronize/protect as required by a proven platform method → independently read back bytes/hash/address/alignment/instructions/branch → repeat observation for idempotence → detach → record physical stock sanity in the authorized future procedure.

If any step cannot prove the expected state, transition to `UNKNOWN`, not `VERIFIED`.

