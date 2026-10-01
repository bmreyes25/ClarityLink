# Step 43G — Setup CF ownership and connection failure cleanup

**Date:** 2026-10-01
**Base commit:** `d3fd5d367d4c097b3b20b0a9aa11cd4ad955448e`
**Scope:** offline static inspection of verified Honda ELF plus a synthetic-only project child lifecycle model. No vehicle, ADB, Honda execution, runtime hooks, binary modification, firmware staging, real keys, or Type111 implementation.

## 1. Artifact and tools

```text
JMCS_PATH: extracted/system/system/bin/jmcs
JMCS_SHA256: cbc7ba881648fb8ffdfcc4c1100a028345c37134a2ae3b9dff7d76572851c232
MATCHES_REFERENCE: YES
```

Tools: Apple `llvm-objdump` via `xcrun` (`--private-headers`, `-d`, `-R`, `-t`), `nm`, `shasum`, and `tools/elf_va_map.py`. The helper parses ELF32/64 little-endian `PT_LOAD` headers and maps file-backed offsets/VAs; its tests cover both Honda load segments, out-of-range and BSS rejection, zero-length boundary behavior, range crossing, and Thumb normalization. `llvm-objdump -R` confirms relocations, and `nm -n` resolves symbols. No decompiler inference is used for the call-site arguments.

ELF program headers establish LOAD #1 `offset=0, VA=0, filesz=memsz=0x33fb50`, and LOAD #2 `offset=0x340988, VA=0x341988, filesz=0xfdac, memsz=0x2e60c`. Therefore file-backed VA translation for LOAD #2 is `file_offset = VA - 0x1000`; VAs in its BSS tail have no file offset. Thumb function pointers are normalized by clearing bit 0 only when mapping function code.

## 2. Setup dictionary callback arguments

At `AirPlayReceiverSessionSetup` (`0x2854e0`), `0x28556a–0x28557c` sets r0=0 (allocator), r1=0 (capacity), r2 to a GOT-loaded pointer at slot `0x3468e4`, and r3 to a GOT-loaded pointer at `0x3468e8`. `llvm-objdump -R` shows `R_ARM_RELATIVE` at both slots; relocation values resolve to `0x3428fc` and `0x342914`. `0x28557e` calls `CFDictionaryCreateMutable`.

These are `kCFLDictionaryKeyCallBacksCFLTypes` and `kCFLDictionaryValueCallBacksCFLTypes`, respectively. Exact words and wrapper targets are in [Setup CF callback tables](../research/carplay/honda-setup-cf-callbacks.md). The callback structs contain retain/release/equal and, for keys, hash; description is NULL. The wrappers branch to Honda `CFLRetain`, `CFLRelease`, `CFLEqual`, and `CFLHash`. Classification: `CF_TYPE` for both key and value callbacks.

## 3. `streams` array callback arguments

At `_AddResponseStream` (`0x284db8`), no existing array yields r0=0, r1=0, and r2 loaded through GOT slot `0x3468ec`. That site has an `R_ARM_RELATIVE` relocation to `kCFLArrayCallBacksCFLTypes` at `0x342858`; `0x284de2` calls `CFArrayCreateMutable`. The table is version 0, Honda retain/release/equality wrappers with a NULL description callback. Classification: `CF_TYPE`.

## 4. Stock Type110 ownership ledger

Setup saves dictionary callback pointers at `sp+0x48/0x4c`. It passes those exact pointers into entry dictionary construction at `0x285956` and screen Type110 entry construction at `0x286086`. The Type110 entry is populated, then passed at `0x286168` to `_AddResponseStream`; `CFArrayAppendValue` reaches `CFLArrayInsertValueAtIndex`, which calls the array retain callback at array offset `+0x0c` before storing the entry. On success, the local entry is released at `0x286300`.

For a newly created `streams` array, `_AddResponseStream` appends the entry, stores the array into the response dictionary at `0x284df8`, and releases its local array reference at `0x284dfe`. The response dictionary value callback retains the array; the array callback retains the entry. The complete symbolic ledger and destructor dispatch are in [Type110 ownership ledger](../research/carplay/honda-type110-ownership-ledger.md).

`CFLRelease` reaches its per-type finalizer table: type 5 maps to `__CFLDictionaryFree` (`0x28f670`) and type 1 maps to `__CFLArrayFree` (`0x28ef70`). Those free paths invoke stored release callbacks over dictionary keys/values and array elements. `_connectionHandleMessage` passes the response to synchronous plist serialization and releases it at `0x28b052`. On the normal no-other-alias stock path, this recursively releases the streams array and Type110 entry after serialization.

## 5. Serialization and HTTP/connection failure

The serializer consumes the CF graph synchronously into separate HTTP body storage. Later queue/write failures do not need CF response graph rollback.

For terminal state-machine read/write errors, `_HTTPConnectionRunStateMachine` (`0x29d698`) stops the connection and invokes its callback at connection offset `+0x20`. `_HTTPServerAcceptConnection` supplies `_HTTPServerCloseConnection` (`0x29d798`) in that callback slot. It removes the connection, stops it, and releases it. Once remaining source/context references drain, `_connectionFinalize` (`0x289d90`) loads the receiver session at per-connection context `+0xf4`, invokes `AirPlayReceiverSessionTearDown` (`0x2852ec`) at `0x289dc6`, and releases/clears the session. Teardown can be deferred until those references are released.

HTTP header commit/queue failure is not proven to take that path: `HTTPConnectionSendResponse` returns the `HTTPHeader_Commit` result, while `_connectionHandleMessage`'s call at `0x28b790` does not test the result. Therefore queue failure's session effect remains UNKNOWN. The receiver-session teardown routine handles Honda-owned streams; it does not provide cleanup for hypothetical project-owned Type111 child state.

## 6. Synthetic project-child cleanup model

Added `response_delivery_model.py` and tests; this is `SYNTHETIC_TEST_VALUE`, not Honda behavior. The model covers entry/population/append failure, successful container ownership transfer, pre-serialization and serialization failure, queue/socket/peer failure after serialization, connection destruction, parent session teardown, idempotent cleanup, Type110/crypto/audio snapshot preservation, and no double close/release. It treats parent connection/session cleanup as a required project lifecycle trigger only as a design hypothesis; no project callback subscription is implemented.

| Scenario | Synthetic graph/listener action | Stock Type110/audio invariant | Evidence class |
|---|---|---|---|
| Entry creation, population, or append failure | Release local candidate and close project listener once | Preserve Type110 response/crypto and audio snapshots | `SYNTHETIC_TEST_VALUE` |
| Append succeeds, before serialization | Candidate graph release path is exercised; listener closes | Preserve snapshots | `SYNTHETIC_TEST_VALUE` |
| Serialization failure | Candidate graph and listener cleanup are idempotent | Preserve snapshots | `SYNTHETIC_TEST_VALUE` |
| Serialization succeeds, then queue/socket/peer failure | CF graph stays released; close project listener | Preserve snapshots | `SYNTHETIC_TEST_VALUE`; Honda graph boundary is independently confirmed |
| Parent connection destruction | Model invokes project cleanup | Preserve snapshots | `HYPOTHESIS` implemented as synthetic contract |
| Parent session teardown, repeated | Graph/listener cleanup is idempotent; no double release/close | Preserve snapshots absent modeled whole-parent changes | `SYNTHETIC_TEST_VALUE` |
| Ordinary successful delivery | Response graph is released after serialization; project listener remains until lifecycle cleanup | Preserve snapshots | `SYNTHETIC_TEST_VALUE` |

The model cannot establish a Honda callback that subscribes a project listener to connection destruction/session teardown, and it does not establish that hypothetical cleanup can leave the Honda session untouched when Honda itself tears down the parent session.

## 7. Readiness

The stock Type110 CF container ownership graph is now proven, and terminal connection/socket failure reaches a receiver-session teardown edge. HTTP queue-commit failure behavior and an exposed project lifecycle subscription remain unresolved. No safe arbitrary post-return mutation/race claim follows.

```text
SETUP RESPONSE CALLBACKS: PROVEN
STREAMS ARRAY CALLBACKS: PROVEN
TYPE110 ENTRY OWNERSHIP: PROVEN (container graph)
STREAMS OWNERSHIP: PROVEN
TYPE110 FINAL RELEASE PATH: PROVEN
SERIALIZATION BOUNDARY: PROVEN
HTTP QUEUE FAILURE CLEANUP: UNKNOWN
SOCKET FAILURE CLEANUP: PROVEN
CONNECTION FAILURE → SESSION EDGE: PROVEN (terminal socket/read error through connection finalizer)
PROJECT CHILD CLEANUP MODEL: NEEDS_MORE_STATIC_PROOF
POST-SETUP SEAM: NEEDS_MORE_STATIC_PROOF
JMCS INTEGRATION DESIGN: NOT READY
JMCS NO-OP TEST: NOT READY
EXTERNALDISPLAY LIVE RENDER TEST: NOT READY
TYPE111 LIVE WORK: NOT READY
LD_PRELOAD STATUS: PARKED
BIGGEST BLOCKER: HTTP queue-commit failure does not have a proven connection/session cleanup transition, and no supported project-owned child lifecycle callback is exposed.
```

## 8. Tests and remaining unknowns

`python3 -m unittest tests.tools.test_elf_va_map -v`: 8 passed. `./tools/run_tests.sh`: unavailable because pytest is not installed (`requirements-test.txt` names the dependency). `python3 -m pytest tests/negotiation/test_response_delivery_ownership.py -q`: unavailable for the same reason (`No module named pytest`). `git diff --check`: PASS. No Honda execution or Type111 implementation occurred. Queue-commit failure, project-child cleanup subscription, and mutation/race safety remain unknown.

## 9. Next action

Recover the `HTTPConnectionSendResponse` header-commit failure branch from `_connectionHandleMessage` through its return to `_HTTPConnectionRunStateMachine`, then determine whether it closes the connection or leaves the receiver session alive.
