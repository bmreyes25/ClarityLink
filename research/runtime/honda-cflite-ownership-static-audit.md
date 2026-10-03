# 43T1-R2 — Honda CFLite Setup response ownership audit

**Scope:** offline disassembly and repository evidence for the preserved `jmcs` ELF. No Honda runtime reads or new private artifacts were used.

## Evidence boundary and chronology

`HONDA_CONFIRMED` Static conclusions below refer to `extracted/system/system/bin/jmcs`, SHA-256 `cbc7ba881648fb8ffdfcc4c1100a028345c37134a2ae3b9dff7d76572851c232`. Relevant prior records: [43G Setup callback and cleanup analysis](../../step-reports/43g-cf-callbacks-failure-cleanup.md), [callback table note](../carplay/honda-setup-cf-callbacks.md), [Type110 ownership ledger](../carplay/honda-type110-ownership-ledger.md), [response lifetime](../carplay/honda-response-ownership.md), [serializer path](../carplay/honda-response-serializer.md), [43H callback fingerprint](../../step-reports/43h-cf-callback-fingerprint.md), and [43H HTTP cleanup](../../step-reports/43h-http-commit-and-session-cleanup.md).

The old 43H uncertainty about constructor callbacks reflects an earlier analysis with an unresolved VA/GOT mapping. The later VA-aware 43G analysis and a fresh offline check of the hash-matched ELF's relocations resolve the callback table addresses for the observed Setup response dictionary, streams array, and Type110 entry. This supersedes that narrow 43H uncertainty; it does not prove every Honda CF operation or lifecycle behavior.

Apple public CoreFoundation APIs/source are `APPLE_CF_REFERENCE` only. Their Create/Copy conventions do not establish Honda CFLite semantics. No Apple source fact is used as Honda ownership proof.

## Object and operation map

| Object / operation | Static evidence and ownership result | Evidence class / risk |
|---|---|---|
| Setup response dictionary | `AirPlayReceiverSessionSetup` creates a mutable dictionary at `0x28557e`, saves callback arguments on its stack, publishes the successful response through the output pointer, and caller later releases it after synchronous serialization. | `HONDA_CONFIRMED`; ownership known for observed path, high confidence within artifact |
| Response dictionary callbacks | Setup passes relocated callback-table pointers resolved from GOT slots `0x3468e4/0x3468e8`; the VA-aware disassembly maps these to Honda's dictionary retain/release/equality/hash callback table. Type110 creation reuses those saved pointers. | `HONDA_CONFIRMED`; table identity resolved for these constructors |
| `streams` array | `_AddResponseStream` creates mutable array with callback table resolved from `0x3468ec` to the observed array callbacks, appends the entry, inserts the array into response, then releases its local array reference. The response dictionary's value callback retains on set. | `HONDA_CONFIRMED`; local +1 and container ownership edge observed |
| Type110 entry dictionary | Setup constructs it with same dictionary callbacks; fills `type=110` and dynamic port fields, then `_AddResponseStream` inserts it in the array. Array insertion callback retains the entry; local entry reference is released after insertion. | `HONDA_CONFIRMED`; observed stock graph edge established |
| Getter wrappers | `CFDictionaryGetValue` / typed getter reach `CFLDictionaryGetValue`; wrapper checks type without retaining. The implementation returns the stored pointer. `CFArrayGetValueAtIndex` likewise returns stored pointer without retain. These are borrowed/+0 for the observed wrappers. | `HONDA_CONFIRMED`; use as borrowed only on these exact wrappers |
| Dictionary setter | `CFLDictionarySetValue` invokes configured key and value retain callbacks on insertion and release callback for a replaced prior value. `CFDictionarySetInt64` creates a `CFNumber`, inserts it, then releases its local temporary. | `HONDA_CONFIRMED`; exact callback path. Does not establish arbitrary callback re-entry safety |
| Array setter | `CFLArrayInsertValueAtIndex` calls the configured value retain callback before storing; array destruction/replacement uses its release callback. | `HONDA_CONFIRMED`; exact observed stock callback table |
| `CFNumber` / `CFString` | Observed scalar helper creates an integer object, inserts it, then releases its temporary. Keys and values in the Setup graph are dictionary-owned through callbacks; full field-by-field cleanup and all string constructor callsites were not exhaustively audited in R2. | `HONDA_CONFIRMED` for observed helper; remainder `UNKNOWN` |
| `CFRetain` / `CFRelease` | `CFRelease` wrapper forwards to `CFLRelease`. Container callbacks route through CFL retain/release helpers. | `HONDA_CONFIRMED` for the observed wrapper paths |
| `_requestSendPlistResponse` | Caller passes the response synchronously to `CFPropertyListCreateData` (binary plist); serializer helper copies data to the HTTP body and releases temporary `CFData`. Caller later releases its response. | `HONDA_CONFIRMED` for static order/lifetime; serializer retention outside call is not proven |
| Failure cleanup | Local Setup helper releases local response/array/entry/number references on observed branches; 43G/43H records describe caller and HTTP cleanup branches. The complete state space under mutation/re-entry and arbitrary failures is not machine-proved. | `HONDA_CONFIRMED` only for listed edges; broader rollback `UNKNOWN` |
| `_AddResponseStream` and callbacks | Calls synchronous CF callback hooks during insertion/replacement. Reentrancy/exception semantics and whether callbacks can observe a partially updated graph are unknown. | `UNKNOWN`; high risk for a hypothetical live mutation |

The above also maps `CFArray`, `CFDictionary`, `CFNumber`, `CFString`, `CFRetain`, `CFRelease`, `CFPropertyListCreateData`, response dictionary, streams array, `_AddResponseStream`, and `_requestSendPlistResponse` at the observed static call path.

## Can a project-created Type111 child be owned safely in theory?

`INFERENCE` At the level of the resolved stock collection callbacks, a new project-created entry inserted into a candidate array would receive a collection retain, and a candidate array inserted into a candidate dictionary would receive its value retain. The project could keep local +1 references until the transaction outcome and release those locals on rollback. This is structurally plausible only if the same callbacks are used, every child field has compatible type/ownership, insertion completes, re-entry is controlled, and serializer lifetime is synchronous as observed.

`MODEL_ONLY` PREP2's `FakeCF` bridge encodes owned local children, retained container insertion, borrowed getters, candidate graph publication and rollback. Focused tests now cover borrowed Honda response/stream/Type110 preservation and child/candidate cleanup. This is an explicit ownership contract model, not a Honda run.

`UNKNOWN` A project-created Type111 child has never been inserted into Honda CFLite. Whether the exact constructor/callback graph tolerates those fields, whether all custom values are compatible, whether failure can interrupt callback/array mutation, and whether cleanup is complete under serializer failure or concurrent observers remain unproved. Do not describe the clean-room bridge as Honda validated: it remains a model, upgraded only in the static stock-container facts listed above.

## Machine-checkable ownership assertions

R2 tests assert (a) the model marks response getters borrowed and never releases borrowed roots, (b) project-owned child/array/dictionary references are balanced after rollback, (c) serializer input remains borrowed by the modeled bridge and its transaction retain is released only at finish, (d) retained Type110 entries survive both rollback and committed candidate ownership, (e) cleanup is idempotent/does not double-release, and (f) the runtime invariant gate rejects absent explicit CF ownership evidence. The model keeps Type110 data untouched; it does not let Type111 cleanup own or mutate a Type110 object.

These checks fail closed on ownership uncertainty. They verify the synthetic reference counter implementation, not native CFLite.

## Remaining unknowns and closure evidence

| Unknown | Risk | Evidence required to close |
|---|---|---|
| Callback behavior for all constructor variants and every key/value | High | Complete version/hash-matched callsite and relocation trace, including all insertion and destruction paths |
| Callback re-entry, concurrent graph mutation, serializer observation | Critical | A safe, separately authorized runtime design and controlled evidence; static disassembly alone is insufficient |
| Failure during collection callback or property-list serialization | High | Complete branch/instruction trace plus native fault-injected compatibility test that does not touch a vehicle, where feasible |
| Type111 field class/coding compatibility with Honda CFLite | Critical | Independent API/schema/source evidence and isolated non-Honda runtime conformance; no R2 evidence establishes it |
| Independent cleanup following host/process loss | Critical | A recovery mechanism independent of the process being modified and demonstrated failure evidence |

No runtime evidence was collected and no new private captures, firmware, addresses, bindings, or binary outputs were added.
