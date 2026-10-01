# Step 43H — CF callback fingerprint and serialization boundary

**Date:** 2026-09-30  
**Starting commit:** `30f6d6b35214331b3cab169f75170b3d82251c41`  
**Scope:** offline static evidence only. No vehicle, ADB, Honda runtime, patching, Type111 implementation, preload, or live rendering.

## Result

The exact callback table arguments for the Setup response dictionary and `streams` array remain unrecovered from the checked-in disassembly. The binary contains named CFL callback tables and prior notes resolve their wrapper behavior, but this does not establish those tables were passed at these particular constructor sites. The focused disassembly does prove that an unrelated global screen array is created with `kCFLArrayCallBacksCFLTypes`, and that `AirPlayReceiverSessionScreen_CopyDisplaysInfo` passes the named CFType dictionary key and value tables. Neither is the Setup response path.

Therefore callback fingerprinting does not upgrade the Setup response dictionary or its streams array to retaining CFType-style Honda proof. Type110 entry ownership remains partial/unknown: append and local array release are recorded, but callback identity and the entry's local reference ledger are not tied together conclusively.

The post-serialization boundary is stronger. `_requestSendPlistResponse` synchronously serializes the response graph into separate HTTP body data; `_connectionHandleMessage` releases the response after the helper returns. Queueing and later socket writes use HTTP message/connection state after that release. A later queue/write failure therefore does not require rollback of the CF response graph. Whether such failure cleans a hypothetical project-owned Type111 listener/session state remains unknown because the connection failure callback target and session teardown edge are not recovered.

## Callback evidence table

| Container/site | Callback evidence | Classification |
|---|---|---|
| Setup response dictionary (`0x28557e`) | Constructor call recorded; argument-to-named-table provenance not present in saved disassembly | UNKNOWN |
| Setup `streams` array (`_AddResponseStream`, `0x284de2`) | Named CFL array table and retain/release wrappers exist; exact constructor argument provenance not established | UNKNOWN |
| Type110 entry dictionary | Exact callback arguments and local release accounting not established | UNKNOWN |
| `/info` display dictionary (`0x287af8`) | Instructions load `kCFLDictionaryKeyCallBacksCFLTypes` (`0x3428fc`) and `kCFLDictionaryValueCallBacksCFLTypes` (`0x342914`) into r2/r3 before constructor | STANDARD_RETAINING_CFSTYLE for this separate dictionary only |
| Global screen array (`0x2a18ae`) | Instructions load `kCFLArrayCallBacksCFLTypes` (`0x342858`) into r2 before constructor | STANDARD_RETAINING_CFSTYLE for this separate array only |

The wrappers previously identified are `__CFLContainerRetain` → `CFLRetain`, `__CFLContainerRelease` → `CFLRelease`, `__CFLContainerEqual` → `CFLEqual`, and `__CFLContainerHash` → `CFLHash`. These establish wrapper semantics for those table records, not use at the unresolved Setup call sites. No table raw words are reported here because the checked-in extracts do not include a verified VA-to-file mapping/dump for those data slots; the earlier raw-offset probe used virtual addresses as file offsets and is invalid evidence.

## Ownership and cleanup decisions

| Decision | Result | Basis |
|---|---|---|
| Type110 entry container retain | UNKNOWN | Exact array callback pointer and entry local release ledger unresolved |
| Streams array container retain | UNKNOWN | Setup array constructor argument unresolved |
| Response owns streams | UNKNOWN | `CFDictionarySetValue` and local array release are present; response value callbacks unresolved |
| Response graph needed after successful serialization | NO | Synchronous serializer returns before caller releases response; later send uses HTTP state |
| Network failure requires CF rollback | NO | Response graph is already released before queue/write failure |
| Network failure requires project stream cleanup | UNKNOWN | Project resource callback/session edge not found |
| Session cleanup edge | PARTIAL | Connection stop/callback behavior noted, callback target-to-session association unknown |

Apple Core Foundation behavior is comparison context only (`EXTERNAL_PLATFORM_BEHAVIOR`): dictionary callback structs govern callback behavior; standard CFType callbacks retain/release values; CFArray copies callbacks and invokes retain/release as elements enter/leave; null callbacks perform no callback. This does not prove Honda used those callbacks at Setup.

## Readiness

**SEAM IMPLEMENTATION DESIGN:** NEEDS_MORE_STATIC_PROOF  
**IMPLEMENTATION READY:** NO  
**LIVE TEST READY:** NO  
**JMCS INTEGRATION READY:** NO  
**EXTERNALDISPLAY LIVE RENDER READY:** NO  
**LD_PRELOAD:** PARKED

The next useful static task is a verified VA-aware dump/disassembly of the exact `0x28557e` and `0x284de2` argument setup plus the Type110 entry construction/release sites, followed by identification of the HTTP connection failure callback's target/session relationship.

## Validation

No tests were requested or run. `git diff --check` and documentation consistency checks are run for this report update.
