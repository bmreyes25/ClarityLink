# R5Y — receiver state machine

Every state below is `MODEL_ONLY_STATE`, not a recovered Honda state. `ReceiverSession.transition` rejects all edges not listed here; tests enumerate the full state-pair matrix.

| From | Legal next states | Meaning |
|---|---|---|
| `IDLE` | `SESSION_CREATED` | Synthetic session object admitted |
| `SESSION_CREATED` | `SETUP_RECEIVED`, `TEARDOWN_PENDING`, `FAILED` | No Setup committed |
| `SETUP_RECEIVED` | `PRIMARY_READY`, `TEARDOWN_PENDING`, `FAILED` | Primary snapshot captured |
| `PRIMARY_READY` | `SECONDARY_NEGOTIATING`, `STREAMING`, `TEARDOWN_PENDING`, `FAILED` | Stock-only model usable |
| `SECONDARY_NEGOTIATING` | `SECONDARY_READY`, `PRIMARY_READY`, `TEARDOWN_PENDING`, `FAILED` | Child prepared or rolled back |
| `SECONDARY_READY` | `STREAMING`, `PRIMARY_READY`, `TEARDOWN_PENDING`, `FAILED` | Child committed; secondary failure can return to primary |
| `STREAMING` | `PRIMARY_READY`, `TEARDOWN_PENDING`, `FAILED` | Symbolic media or primary-only activity |
| `TEARDOWN_PENDING` | `CLOSED` | Cleanup in fixed order |
| `FAILED` | `TEARDOWN_PENDING` | Fatal model invariant route only |
| `CLOSED` | none | Terminal; duplicate teardown is an idempotent no-op |

The current facade creates sessions directly into `SESSION_CREATED`; `FAILED` is reserved for a future whole-model invariant fault and cannot be reached by an ordinary secondary failure. Setup validation, optional resource failures, and media failures contain the child and return to `PRIMARY_READY`. `TEARDOWN_PENDING` always resolves to `CLOSED` for the built-in mocks, even when a synthetic teardown error is recorded. Superseding a generation closes the old session before creating the newer one. Old frames and cleanup never address the new generation.
