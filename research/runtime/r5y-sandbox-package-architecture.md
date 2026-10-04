# R5Y — reusable sandbox package architecture

**MODEL_ONLY · HOST_ONLY · NOT_DEPLOYABLE · NOT_HONDA_BINARY · NOT_REAL_CARPLAY · NOT_MFI · NO_REAL_JMCS_PATCH.** The importable package is `src/claritylink-sandbox/r5y_receiver_core/`. The R5X `type111_patch_model.py` remains unchanged for historical imports and tests. R5Y uses its own small package because state, adapter contracts, orchestration, and replay now have different responsibilities.

| Module | Responsibility | Public API | Dependencies | Forbidden dependencies | Future extension point |
|---|---|---|---|---|---|
| `model.py` | Frozen values, states, canonical synthetic serializer, primary snapshot | `SessionGeneration`, `ReceiverState`, `SetupRequest`, `SetupResponse`, frames, snapshots | Python dataclasses, enum, JSON | Honda/Apple code, file/network/device I/O | Typed values crossing an evidence-backed adapter |
| `adapters.py` | Protocols and symbolic providers/handles | Listener, security, decoder, display provider contracts and mocks | `model.py`, typing | Real listeners, crypto, media, Android display | New provider only after separate evidence and review |
| `core.py` | Coordinator, transaction, cleanup, fault injection, event trace | `ReceiverCore`, `SetupTransaction`, `CleanupManager`, `FaultInjector` | `model.py`, `adapters.py` | Target hook, loader, packet parser, binary code | Keep this tested core unchanged where possible |
| `replay.py` | Pure interpretation of synthetic step mappings | `replay_document` | Package API, typing | File and device access | Host fake/replay adapter only |
| `__init__.py` | Stable re-export surface | Listed [public API](r5y-public-sandbox-api.md) | Above modules | Dynamic loading | Versioned model contract |
| `type111_patch_model.py` | Preserved R5X proof-of-concept | Original R5X names | Standard library only | Target dependencies | Historical compatibility, not new integration |

All code under the sandbox path is checked by [the scoped firewall](../../tools/check_r5y_sandbox_boundary.py). The [fixture CLI](../../tools/r5y_replay.py) is a host tool that reads only `tests/fixtures/r5y/*.json`; it imports the pure replay function. This structure deliberately does not import the older Honda-facing negotiation, legacy crypto, or Android renderer models. Their useful ideas—generation ownership, stock-first rollback, and stale clearing—are re-expressed with invented symbolic data rather than copying target-specific behavior.
