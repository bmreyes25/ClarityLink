# Step 31 — find the phone-facing AirPlay server-info consumer

**Date:** 2026-09-29  
**Starting commit:** `a5e8b3f`  
**Scope:** offline-only static analysis. No vehicle, ADB, ptrace, firmware patch, live hook, Type-111 implementation, decoder/rendering, or registry work.

## Inputs and method

Used the identity-verified `extracted/system/system/bin/jmcs` and the mapped-module inventory captured from the disconnected `jmcs` process. The inventory identifies 45 mapped `.so` modules. Inspected ARM ELF regular and dynamic symbols, relocations, strings, disassembly, and dynamic imports/exports with LLVM ELF tools. Inspected imports/exports of the exact acquired shared objects corresponding to the mapped set. Existing Step 30 establishes the matching `jmcs` hash and local function dataflow.

## Findings

### 1. `AirPlayCopyServerInfo` visibility

`AirPlayCopyServerInfo` is `GLOBAL` in `.symtab` at `0x282cd4` (size `0x8c4`). It is absent from `.dynsym`; `llvm-objdump -T` and `llvm-nm -D` do not list it. It is therefore not an ordinary ELF dynamic export and cannot be imported through standard shared-library symbol resolution. `PLT/GOT`: no dynamic symbol or import relocation for this function was found.

### 2. Mapped shared libraries

Searched dynamic symbols of the mapped acquisition libraries for the builder and its related property/display functions. No import, export, or dynamic relocation match was found. No external library consumer is identified. This closes the specific normal ELF-import possibility raised for this pass, while leaving private address passing or other runtime mechanisms theoretically possible.

### 3. Dynamic lookup

`jmcs` imports `dlopen` and `dlsym`. Disassembly has loader callsites at `0x121aec` onward and `0x18d9ba`, associated with generic dynamic/SQLite loader support. Strings contain the function's symbol name in ELF debug/symbol material, but not as a runtime lookup key; the printable strings scan found no lookup literal `AirPlayCopyServerInfo`. Result: `DYNAMIC_LOOKUP=UNKNOWN` overall; no evidence it is dynamically resolved. The generic presence of `dlsym` is not evidence of a server-info lookup.

### 4. Function-pointer tables and indirect callers

No relocation, initializer, or recovered function-pointer table slot containing `AirPlayCopyServerInfo` was found. The function is not dynsym-visible, and the complete `jmcs` call/reference sweep previously found no direct call. A definite indirect consumer/table type/slot/consumer cannot be recovered from the available static artifacts. Result: no table-backed consumer established.

### 5. Reverse from plist response and HTTP send

The known `_requestSendPlistResponse` caller is `_connectionHandleMessage` at `0x28afba`. Its object is the response output slot produced by `AirPlayReceiverSessionSetup` at `0x28af72`. That object is synchronously serialized to binary plist (`format=0xc8`) and sent through `HTTPConnectionSendResponse` (`0x29dbe4`), then `_HTTPConnectionRunStateMachine` -> `SocketWriteData` -> `writev@plt`.

No response callsite was found whose object is the `AirPlayCopyServerInfo` return, or a wrapper demonstrably populated from it. This serializer/send chain is confirmed only for SETUP. The `/info` literal exists in `jmcs`, but its request dispatch and builder relationship remain unrecovered. No request/path table can responsibly be supplied for server info.

### 6. Local display object and mutation

Prior evidence remains: `AirPlayReceiverSessionPlatformCopyProperty` (`0x28d328`) handles `displays` by creating a mutable array, appending one main-display dictionary from `AirPlayReceiverSessionScreen_CopyDisplaysInfo` (`0x287ae0`), and returning the array. `AirPlayCopyServerInfo` inserts the returned property at `0x282e42` into its mutable dictionary and returns it. Array and enclosing dictionary are mutable/replaceable locally. Since the receiving caller and serializer boundary are unknown, the last safe phone-facing mutation point is unknown.

### 7. Type 111 and architecture status

Prior static parsing remains unchanged: `AirPlayReceiverSessionSetup` (`0x2854e0`) handles stream types 100/101 as audio, 110 as screen, and 111 via the invalid-type branch at `0x2861f6`. Exact external error status, full partial side effects, and live hook ABI remain unknown. The setup loop processes the request array; without rollback/atomicity evidence, per-entry delegation is unknown. No display UUID-to-Type-111 binding is established. The two-hook design remains a candidate only.

## Decision gate

```text
AIRPLAYCOPY_SERVERINFO SYMBOL: GLOBAL in .symtab; not exported in .dynsym
EXTERNAL CONSUMER: none found among 45 mapped .so modules
PHONE_REQUEST_HANDLER: UNKNOWN; /info literal exists, no proven binding
SERVER_INFO_SERIALIZER: UNKNOWN
SERVER_INFO_SEND_PATH: UNKNOWN
DISPLAYS_PHONE_FACING: UNKNOWN
SERVER_INFO_MUTATION_POINT: UNKNOWN at phone-facing boundary
DISPLAY_ARRAY: MUTABLE; outer dictionary mutable
TYPE111_REJECTION_STATUS: invalid-type path at 0x2861f6; external status unknown
TYPE111_INTERCEPT_ABI: UNKNOWN; conceptual per-entry dispatch only
PARTIAL_SETUP_DELEGATION: UNKNOWN
DISPLAY_STREAM_BINDING: UNKNOWN
TWO_HOOKS_SUFFICIENT: UNKNOWN
OFFLINE IMPLEMENTATION READY: NO
LIVE CONNECTION TEST READY: NO
BIGGEST BLOCKER: no recovered consumer of AirPlayCopyServerInfo's return value
```

## Deliverables and next action

Updated the server-info consumer/send-path, display capability, Type-111, correlation, and architecture notes, and project state/index/action records. No code or data models changed, so tests were not run. Run `git diff --check` before commit.

**Next action:** recover the `/info` request handler from its string xrefs/HTTP dispatch and establish whether it calls a separate internal wrapper or a second builder; continue from the proven fact that the external shared-library import route is absent.
