# R5Y — public host-only sandbox API

The stable import surface is `r5y_receiver_core` after adding `src/claritylink-sandbox` to a host Python path. It is a symbolic model API, **not a receiver API**. `LABELS` includes `MODEL_ONLY`, `HOST_ONLY`, `NOT_DEPLOYABLE`, `NOT_HONDA_BINARY`, `NOT_REAL_CARPLAY`, `NOT_MFI`, and `NO_REAL_JMCS_PATCH`.

| Concept | Public type/function | Contract |
|---|---|---|
| Session identity | `SessionGeneration` | Positive immutable integer; monotonically increasing in a `ReceiverCore` |
| Session state | `ReceiverSession`, `ReceiverState` | Explicit `MODEL_ONLY_STATE` transition table |
| Setup | `SetupRequest`, `SetupResponse`, `StreamDescriptor`, `SetupTransaction` | Invented, validated, immutable response values; commit once or idempotent abort |
| Primary | `PrimaryStreamState`, `PrimarySnapshot`, `capture_primary`, `primary_preserved` | Parent-owned opaque synthetic state and preservation oracle |
| Secondary | `SecondaryStreamState`, `ListenerHandle`, `SecurityContext` | One generation-owned optional child |
| Media | `MediaFrame`, `DecodedFrame`, `DisplayFrame` | Symbolic strings and ordered sequence numbers only |
| Display | `DisplaySink`, `MockDisplay1Sink` | One symbolic frame and explicit clear state |
| Cleanup | `CleanupManager`, `CleanupResult`, `ResourceSnapshot` | Exact-generation, ordered, idempotent child cleanup and counts |
| Errors/faults | `ReceiverError`, `FailurePoint`, `FaultInjector` | Sanitized error codes and named deterministic one-shot faults |
| Serializer | `serialize_setup` | Canonical JSON tagged `SYNTHETIC_MODEL_SERIALIZER` / `NOT_CARPLAY_WIRE_FORMAT` |
| Orchestration | `ReceiverCore` | Create, setup, stream, clear, teardown, snapshot, primary oracle |
| Replay | `replay_document` | Pure mapping-in/result-out synthetic event replay |

Value dataclasses are frozen where stable snapshots matter; resource handles and sessions are mutable only through explicit methods/transitions. There is no global mutable receiver state. A `ReceiverCore` instance owns its own sessions and events. Unknown states and illegal transitions raise `ReceiverError`. The [state machine](r5y-receiver-state-machine.md), [transaction contract](r5y-setup-transaction-engine.md), and [adapter contract](r5y-future-adapter-contract.md) define the supported evolution boundary. No compatibility with Honda data structures is implied.
