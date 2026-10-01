# Honda stock Type110 CF ownership ledger — Step 43G

**Artifact:** hash-matched Honda `jmcs` SHA-256 `cbc7ba881648fb8ffdfcc4c1100a028345c37134a2ae3b9dff7d76572851c232`. Static, instruction-level result. Detailed callback addresses: [Setup callback tables](honda-setup-cf-callbacks.md). Full milestone: [Step 43G report](../../step-reports/43g-setup-cf-ownership-and-network-cleanup.md).

## Reference/ownership ledger

| Step | Object | Operation | Reference effect | Proven callback/function | Resulting owner(s) | Confidence |
|---|---|---|---|---|---|---|
| 1 | Setup response dictionary | create at `0x28557e` | +1 creation reference | `CFLDictionaryCreate`; CFType key/value tables | Setup local | HONDA_CONFIRMED |
| 2 | Type110 entry dictionary | create at `0x286086` | +1 creation reference | same callback pointers saved at Setup `sp+0x48/0x4c` | Setup local (`r5`) | HONDA_CONFIRMED |
| 3 | Entry keys/values | `CFDictionarySetInt64` and other setters | container retains inserted objects; helper temporary handling varies by helper | key/value callbacks → `CFLRetain` | entry plus any helper temporaries | HONDA_CONFIRMED for container callback; field-temporary ledger PARTIAL |
| 4 | Streams array | create at `_AddResponseStream` `0x284de2` when absent | +1 creation reference | `CFLArrayCreate` copies type callbacks | `_AddResponseStream` local (`r8`) | HONDA_CONFIRMED |
| 5 | Type110 entry | `CFArrayAppendValue` at `0x286168` → `CFLArrayAppendValue` → `CFLArrayInsertValueAtIndex` | +1 array retain before storing element | array callback at object +0x0c → `__CFLContainerRetain` → `CFLRetain` | local + streams array | HONDA_CONFIRMED |
| 6 | Streams array | response `CFDictionarySetValue` at `0x284df8` | +1 response-dictionary value retain | dictionary value callback → `CFLRetain` | local + response dictionary | HONDA_CONFIRMED |
| 7 | Streams array | local `CFRelease` at `0x284dfe` | -1 local reference | `CFRelease` → `CFLRelease` | response dictionary only | HONDA_CONFIRMED |
| 8 | Type110 entry | local `CFRelease` at `0x286300` after append success | -1 local reference | `CFRelease` → `CFLRelease` | streams array only | HONDA_CONFIRMED |
| 9 | Response dictionary | publish to `responseOut` at `0x286260` | ownership remains +1 and passes to caller | output pointer store | caller | HONDA_CONFIRMED |
| 10 | Response dictionary | synchronous plist serialization; caller `CFRelease` at `0x28b052` | caller's +1 released | `CFRelease` → `CFLRelease` | none after destructor path | HONDA_CONFIRMED |
| 11 | Nested graph | dictionary/array finalization | callback-based recursive releases | `CFLRelease` type table: type 5 → `__CFLDictionaryFree`; type 1 → `__CFLArrayFree`; free routines invoke installed release callbacks | descendants released when their last owning reference reaches zero | HONDA_CONFIRMED |

**No unsupported retain count is inferred.** For the ordinary stock path, after each local release, the entry has its array-owned reference and the array has its response-owned reference. The response holds its caller reference through serialization. The wrapper callbacks and destructor table establish the nested release path.

```text
TYPE110_ENTRY_RETAINED_BY_ARRAY: YES
STREAMS_ARRAY_RETAINED_BY_RESPONSE: YES
TYPE110_LOCAL_RELEASE_AFTER_APPEND: YES
STREAMS_LOCAL_RELEASE_AFTER_DICTIONARY_INSERT: YES
TYPE110_ENTRY_FINAL_RELEASE_PATH: caller CFRelease(response) → CFLRelease(type 5) → __CFLDictionaryFree → CFLDictionaryRemoveAllValues → release streams value → CFLRelease(type 1) → __CFLArrayFree → CFLArrayRemoveAllValues → release Type110 entry → CFLRelease(type 5) → __CFLDictionaryFree
TYPE110_OWNERSHIP_LEDGER: COMPLETE (container graph); PARTIAL (all scalar/helper temporaries)
```

## Future insertion design contract (not an implementation)

- `FUTURE_ENTRY_CREATE_RULE`: use an owned mutable entry dictionary with the proven Honda key/value callback tables; callback identity is now Honda-confirmed.
- `FUTURE_ENTRY_APPEND_RULE`: append through the confirmed retaining `streams` array; the array takes a retain on successful insertion.
- `FUTURE_ENTRY_LOCAL_RELEASE_RULE`: after successful append, the local entry reference may be released, matching the stock Type110 path.
- `PRE_APPEND_FAILURE_RULE`: release project-local CF objects and close project-local resources.
- `POST_APPEND_FAILURE_RULE`: remove the inserted entry from the array (the array release callback is proven) or discard an independently owned candidate graph; exact caller rollback/error-response behavior is not proven.
- `RESPONSE_RELEASE_RULE`: caller releases the response after synchronous serialization; do not separately release an entry once only the array owns it.

These rules concern CF object lifetime only. They do not make arbitrary post-return mutation race-free or establish the HTTP failure callback as an available project hook.
