# Honda CF callback ownership — Step 43G

**Scope:** static, offline review of the hash-identified `jmcs` ELF (`cbc7ba881648fb8ffdfcc4c1100a028345c37134a2ae3b9dff7d76572851c232`) and prior disassembly notes. No runtime, patching, Type111 implementation, or device testing.

## Callback tables and certainty

The ELF symbol notes identify `kCFLArrayCallBacksCFLTypes` at `0x342858`, dictionary key callbacks at `0x3428fc`, and dictionary value callbacks at `0x342914`. The recorded table entries point to CFL container wrappers. Their function behavior can be described, but the Setup response dictionary's constructor arguments at `0x28557e` have not been unambiguously mapped to the named key/value tables. The table's presence in the ELF is not proof it is the one passed by this call site.

| Container | Callback slot | Function / address | Semantics | Confidence |
|---|---|---|---|---|
| Mutable array | retain | `__CFLContainerRetain`, `0x28ebc4` (table entry `0x28ebc5`) → `CFLRetain`, `0x28eb70` | Retains inserted element | `HONDA_INDIRECT_CANDIDATE`: named table and wrapper recorded; precise Setup array call-site relocation should be revalidated against the ELF |
| Mutable array | release | `__CFLContainerRelease`, `0x28ec48` (entry `0x28ec49`) → `CFLRelease`, `0x28ebcc` | Releases element when removed/container destroyed | `HONDA_INDIRECT_CANDIDATE` |
| Mutable array | equality | `__CFLContainerEqual`, `0x28ecd8` (entry `0x28ecd9`) → `CFLEqual`, `0x28ec50` | Compares values | `HONDA_INDIRECT_CANDIDATE` |
| Mutable array | copy description | NULL | No callback | `HONDA_INDIRECT_CANDIDATE` |
| Dictionary key | retain | `__CFLContainerRetain`, `0x28ebc4` | Retains key | Table bytes/symbol recorded; Setup association unresolved (`HONDA_INDIRECT_CANDIDATE`) |
| Dictionary key | release | `__CFLContainerRelease`, `0x28ec48` | Releases key | Table bytes/symbol recorded; Setup association unresolved (`HONDA_INDIRECT_CANDIDATE`) |
| Dictionary key | equality | `__CFLContainerEqual`, `0x28ecd8` | Compares keys | Table bytes/symbol recorded; Setup association unresolved (`HONDA_INDIRECT_CANDIDATE`) |
| Dictionary key | hash | `__CFLContainerHash`, `0x28ed24` (entry `0x28ed25`) → `CFLHash`, `0x28ecdc` | Hashes keys | Table bytes/symbol recorded; Setup association unresolved (`HONDA_INDIRECT_CANDIDATE`) |
| Dictionary value | retain | `__CFLContainerRetain`, `0x28ebc4` | Retains value | Table bytes/symbol recorded; Setup association unresolved (`HONDA_INDIRECT_CANDIDATE`) |
| Dictionary value | release | `__CFLContainerRelease`, `0x28ec48` | Releases value | Table bytes/symbol recorded; Setup association unresolved (`HONDA_INDIRECT_CANDIDATE`) |
| Dictionary value | equality | `__CFLContainerEqual`, `0x28ecd8` | Compares values | Table bytes/symbol recorded; Setup association unresolved (`HONDA_INDIRECT_CANDIDATE`) |
| Dictionary value | copy description | NULL | No callback | Table bytes/symbol recorded; Setup association unresolved (`HONDA_INDIRECT_CANDIDATE`) |

The CFL constructors copy supplied callback structures into container state. A NULL callback-structure argument is zeroed by the constructor, so such a container would not retain/release through that callback slot. This is constructor behavior, not proof that Honda Setup passed NULL or a particular named table. `_AddResponseStream` uses `CFArrayCreateMutable`, `CFArrayAppendValue`, and `CFDictionarySetValue`; the stream-entry dictionaries are created via a separate helper path and their callback arguments are not tied conclusively to the named tables here.

```text
DICTIONARY CALLBACKS: PARTIAL
ARRAY CALLBACKS: PARTIAL
```

## Stock Type110 ownership ledger

| Object | Create site | Insert site | Container retain? | Local release? | Final owner / normal release | Failure release | Confidence |
|---|---|---|---|---|---|---|---|
| Setup response dictionary | Setup `CFDictionaryCreateMutable`, `0x28557e` | Receives `streams` and other response fields | Constructor callback identity unresolved | Published to caller on success | Caller holds response through serialization; releases at `0x28b052` | Setup's internal error branch releases local response; exact callback cascade depends on unresolved table association | `HONDA_CONFIRMED` dataflow; retain graph `HONDA_INDIRECT_CANDIDATE` |
| `streams` array | `_AddResponseStream`, `CFArrayCreateMutable` at `0x284de2` if absent | Appended at `0x284dea`/`0x284e10`, attached with `CFDictionarySetValue` at `0x284df8` | Callback table appears to be CFL type callbacks; exact table-to-callsite relocation needs revalidation | Helper releases its local array reference at `0x284dfe` | Nested under response; response release at caller `0x28b052` | Response graph cleanup on Setup failure; exact cascade is callback-dependent | `HONDA_INDIRECT_CANDIDATE` |
| Type110 stream entry dictionary | `_AddResponseStream` path | Appended to `streams` | Entry-array retain callback unresolved at its exact constructor call | Local release site/accounting not established from available record | Expected nested owner is streams array, not established as exact retain ledger | Setup failure cleanup path exists; entry release count unresolved | `HONDA_UNKNOWN` |
| Entry keys/values | Stream-entry population helpers | `CFDictionarySetValue` calls | Dictionary callbacks unresolved at exact constructor call | Per-field local release sites not fully established | Expected dictionary ownership only if retain callback installed | Setup failure graph cleanup depends on callbacks | `HONDA_UNKNOWN` |

```text
STOCK OWNERSHIP LEDGER: PARTIAL
```

## Future project ownership contract (requirements only)

No implementable retain/release contract follows until the constructor-to-callback references and getter ownership are resolved. Safe interim rule for any later design: project owns every newly created object and fd; do not mutate the original stock graph until a complete candidate exists; after append, treat any failure as requiring explicit removal or candidate-graph discard before returning stock response. Never assume container retention or borrowed getter semantics.

| Object | Before append | Success ownership | Pre-append failure | Post-append failure | Evidence |
|---|---|---|---|---|---|
| Type111 response dictionary | Project owns its creation reference | Response array may own it only if retain callback is proven; project releases local ref only after that proof | Release candidate | Remove from candidate or discard candidate graph; do not leave entry visible in stock graph | `HYPOTHESIS` |
| Copied request fields / numbers / strings | Project owns copies/temporaries | Candidate dictionary owns only if its value/key callbacks retain | Release each created object | Discard candidate graph and project refs | `HYPOTHESIS` |
| Listener/fd | Project owns | Project stream state owns | Close exactly once, mark invalid | Close through project cleanup; never Honda teardown | `HYPOTHESIS` |
| Project stream/security state | Project owns | Project-only session association | Free and zero security material | Independently clean on serializer/queue/send error | `HYPOTHESIS` |
| Retained streams array reference | Unknown until getter semantics proven | Project releases its extra reference only if getter returns +1 / explicit retain succeeds | Release only known +1 refs | Do not release a borrowed stock reference | `HONDA_UNKNOWN` |
| Scratch dictionaries/arrays | Project owns | Candidate parent owns only if callbacks are proven | Release temporaries | Discard candidate graph and remaining local refs | `HYPOTHESIS` |

```text
PROJECT OWNERSHIP CONTRACT: PARTIAL
```

## Failure and cleanup edges

| Failure | Propagation and body state | CF response released? | Request released? | Type110 / project impact | Confidence |
|---|---|---|---|---|---|
| `CFPropertyListCreateData` / binary plist creation fails | Serializer returns HTTP 500; body setter is not reached, so no new serialized body is installed on this path | Yes, caller reaches common cleanup and releases response at `0x28b052` | Yes, common cleanup at `0x28b048` | Response bytes not emitted as successful plist; if project state was allocated, cleanup edge is not established | `HONDA_CONFIRMED` path; prior body state not fully audited |
| `CFDataGetBytePtr` / `CFDataGetLength` | Recorded caller feeds these into body installation; exact null/error guards are not established in the retained disassembly record | Yes on ordinary serializer return | Yes | Input/body behavior at invalid data is unknown; do not claim clean rollback | `HONDA_UNKNOWN` |
| `HTTPMessageSetBody` fails | Returns error / helper reports 500. Body-length setup can free or replace prior body storage before later allocation/copy/header failure; partial HTTP message mutation is possible | Yes | Yes | Original CF graph remains untouched, but HTTP error response may encounter partially updated message state. Project cleanup remains separate | `HONDA_INDIRECT_CANDIDATE` |
| `HTTPHeader_Commit` / `HTTPConnectionSendResponse` fails | Queue function returns error; handler's recorded flow does not branch on its return before common continuation | Already released; response graph is independent | Already released | HTTP message/connection owns serialized bytes; project listener/state cleanup is not linked | `HONDA_CONFIRMED` for queue edge, cleanup callback unknown |
| Later `writev` fails | State machine stops connection and invokes connection callback if present | No longer live/needed | No longer live/needed | No response-graph mutation possible; project cleanup depends on untraced callback/session relationship | `HONDA_CONFIRMED` send path; project cleanup `HONDA_UNKNOWN` |

The serializer reads the response graph synchronously and produces separate `CFData`; the caller releases the graph after the helper returns. The HTTP body is separately installed in the HTTP message. The send state machine later uses connection-owned buffers and `writev`, not the CF response object. Thus a later queue/write failure cannot require retaining or mutating the response graph. It can still require project-owned listener/state cleanup, for which no concrete callback-to-project edge has been proven.

```text
SERIALIZATION FAILURE CLEANUP: PARTIAL
HTTP QUEUE CLEANUP: PARTIAL
CALLER SIDE MUTATION RACE: NO_STATIC_EVIDENCE
```

`NO_STATIC_EVIDENCE` means this inspected path shows Setup publishing the response only to the caller's responseOut slot before serialization; it does not establish thread dispatch, global non-escape, or runtime race freedom.

## Rollback matrix and decision

| Failure | Project objects to release | Response graph state | Stock response preserved? | Type110 impact | Confidence |
|---|---|---|---|---|---|
| Before project dictionary creation | Any already allocated listener/state; preferably none | Untouched stock response | Yes | None | `HYPOTHESIS` |
| After candidate dictionary creation, before append | Candidate and copied fields; close listener; erase state/secrets | Untouched stock graph if candidate is separate | Yes | None | `HYPOTHESIS` |
| During append | Candidate graph plus all project refs; rollback must remove partial insertion or discard candidate response | Direct in-place mutation rollback is not proven | Unknown without candidate strategy | Potential stock alteration if partial mutation occurred | `SYNTHETIC_TEST_VALUE` model only |
| After append, before serializer | Project state; candidate entry/container changes | If original graph was mutated, no Honda-confirmed rollback edge | Not proven | Could alter stock response on failure | `HONDA_UNKNOWN` |
| Serializer failure after append | Project state requires independent cleanup | CF response released by caller; serialized body may be absent/partially installed depending failure | No successful stock fallback is shown | Stock entry may be in failed response; no successful Type110 response guaranteed | `HONDA_UNKNOWN` |
| HTTP queue failure after serializer | Project listener/state through independent project lifecycle | CF graph already released; HTTP message has serialized bytes | No successful send proven | No graph mutation; delivery failure only | `HONDA_UNKNOWN` for project cleanup |
| Later socket/write failure | Project listener/state through independent project lifecycle | CF graph no longer live; connection stops/callback runs | No successful delivery | No graph mutation; delivery failure only | `HONDA_UNKNOWN` for callback ownership |
| Unexpected stock Setup failure | None should have been allocated before success | Honda-authored failure path | No success response | Stock behavior unchanged | `HONDA_CONFIRMED` |

The candidate is still `NEEDS_MORE_STATIC_PROOF`: dictionary callback arguments and stock entry ledger are incomplete, so the project ownership contract cannot be Honda-derived; serializer body failure can partially mutate HTTP message state; and no callback/session edge links later queue/write failure to hypothetical project resources. Implementation, live, jmcs integration, and ExternalDisplay gates remain closed; LD_PRELOAD remains parked.

**Next static question:** Can the exact Setup dictionary callback arguments and Type110 entry construction/release sites be recovered from the identity-verified `jmcs` ELF, while also identifying the connection failure callback's target and any session teardown edge?
