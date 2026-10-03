# CoreFoundation bridge contract — 43T1-PREP2

**Decision: `CF_BRIDGE_OFFLINE_READY` as a clean-room contract only.** Implementation: `src/claritylink-negotiation/prep2_cf_bridge.py`. Tests: `tests/prep2/test_prep2_models.py`. Evidence class: `LAB_SYNTHETIC_CONFIRMED`. Honda CF runtime ABI remains unproven.

## Contract

- Request, response, streams array, session, connection, and message pointers are borrowed Honda-owned inputs. The model retains no caller/response pointer after `finish_type111`.
- It validates response/array types, presence, duplicate Type111, bounded stream count, and port range before mutation. The only project entry is `{type: 111, dataPort: P}`. Existing entries, Type110, ordering, and unknown metadata are preserved.
- It allocates both CFNumber-shaped values, the dictionary, and a new mutable array before changing the response. The copy is modeled with the statically present `CFArrayCreateMutable` + `CFArrayAppendValue` pair. A final `CFDictionarySetValue` is the only response graph change; no project socket, decoder, or rendering code enters this bridge.
- The ownership ledger is `OWN_TYPE_NUMBER`, `OWN_PORT_NUMBER`, `OWN_STREAM_DICTIONARY`, `OWN_MUTABLE_STREAMS_COPY`, and a synchronous `OWN_ORIGINAL_STREAMS_TEMP_RETAIN` used only to restore the exact previous array if needed. Honda response/array pointers are never released by the model.
- On failure before `SetValue`, creator-owned objects are released and the stock response is unchanged. After commit, serializer failure attempts to restore only the exact previous `streams` object, guarded by identity. If restoration fails or the response changed, the failure is surfaced; the model does not claim stock restoration. Project temporary references are still released deterministically.
- Nested and concurrent transactions use independent transaction objects and have no global current-response slot.

The fake runtime checks identity, type, retain/release, use after release, double release, append, set, and deterministic allocation failures. It is a test double, not Honda `CFLite`. Static Honda response mutability and synchronous lifetime are compatible with studying this model, but neither arbitrary callout safety nor post-Setup callback ownership is established. See [static map](honda-cf-setup-response-map.md).

## Offline test result

Focused PREP2 tests exercise Type110-only/nonmutation, append/order, duplicate rejection, unknown entry preservation, every allocation stage, precommit rollback, serializer-failure rollback, response replacement races, commit cleanup, ownership misuse, separate transactions, and bounded malformed arrays. A rollback failure caused by an injected `CFDictionarySetValue` failure is intentionally a surfaced failure, not a passing “restored” state.

This result authorizes no Honda CF call, Type111 negotiation, patch, or live experiment.
