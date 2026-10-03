# Honda Setup CoreFoundation response map — 43T1-PREP2

**Classification:** read-only static map of preserved `extracted/system/system/bin/jmcs` (`ELF32`, ARM, little-endian, EABI5; SHA-256 `cbc7ba881648fb8ffdfcc4c1100a028345c37134a2ae3b9dff7d76572851c232`). No Honda runtime or vehicle was contacted.

## CF-style symbols verified in the preserved ELF

The following names are internal symbols in this Honda `CFLite`-backed implementation, not proof that Apple's CoreFoundation ABI is interchangeable:

| Capability | Present symbols / evidence | Classification |
|---|---|---|
| Generic/type checks | `CFGetTypeID` (`0x28e2fc`), `CFArrayGetTypeID` (`0x28e330`), `CFDictionaryGetTypeID` (`0x28e4ac`), `CFNumberGetTypeID` (`0x28e546`), `CFStringGetTypeID` (`0x28e56c`) | `HONDA_STATIC_COMPATIBILITY` |
| Dictionary lookup/mutation | `CFDictionaryGetValue` (`0x28e520`), `CFDictionarySetValue` (`0x28e532`), `CFDictionaryRemoveValue` (`0x28e53a`), `CFDictionaryCreateMutable` (`0x28e4b0`), `CFDictionaryGetCount` (`0x28e50e`) | `HONDA_STATIC_COMPATIBILITY` |
| Array lookup/mutation | `CFArrayGetCount` (`0x28e35c`), `CFArrayGetValueAtIndex` (`0x28e36e`), `CFArrayAppendValue` (`0x28e380`), `CFArrayCreateMutable` (`0x28e346`), `CFArrayCreateCopy` (`0x28e334`) | `HONDA_STATIC_COMPATIBILITY` |
| Number construction/query | `CFNumberCreate` (`0x28e54a`), `CFNumberGetValue` (`0x28e55c`) | `HONDA_STATIC_COMPATIBILITY` |
| String construction/query | `CFStringCreateWithBytes` (`0x28e570`), `CFStringCreateWithCString` (`0x28e600`), `CFStringGetCString` (`0x28e654`), `CFStringGetLength` (`0x28e620`) | `HONDA_STATIC_COMPATIBILITY` |
| Lifetime | `CFRetain` (`0x28e30e`), `CFRelease` (`0x28e312`) | `HONDA_STATIC_COMPATIBILITY` |
| Property-list serialization | `CFPropertyListCreateData` (`0x28e6fc`); Setup caller invokes it synchronously through `_requestSendPlistResponse` | `HONDA_CONFIRMED` for this observed path |

`CFDictionaryCreateMutableCopy` and `CFArrayCreateMutableCopy` were not found as named wrapper symbols; `CFArrayCreateCopy` is present but does not establish a mutable copy. `CFLStringGetTypeID` exists at `0x28fa46`; a separately named `CFStringGetTypeID` wrapper is present. This is a preserved-binary symbol inventory, not a claim that unlisted APIs cannot exist through another route.

## Setup response construction and lifetime

| Finding | Evidence | Classification |
|---|---|---|
| Setup creates the response with `CFDictionaryCreateMutable` at `0x28557e`, then publishes the same pointer through its output on success at `0x286260`. | `honda-setup-cf-callbacks.md`; `honda-post-setup-caller-liveness.md` | `HONDA_CONFIRMED` |
| `_AddResponseStream` at `0x284db8` obtains `streams`; if absent it creates a mutable array, appends the stock entry and sets it on the response; if present it appends to that array. | `honda-post-setup-caller-liveness.md` | `HONDA_CONFIRMED` |
| Stock Type110 construction appends entries in Setup order; the stream helper does not replace or reorder prior entries. The Type110 ownership ledger records its local release after append and array ownership. | `honda-setup-response.md`; `honda-type110-ownership-ledger.md` | `HONDA_CONFIRMED` for Honda's own path |
| `_connectionHandleMessage` passes the same response to `_requestSendPlistResponse` at `0x28afba`; serialization is synchronous, and the caller releases the response at `0x28b052`. | `honda-post-setup-caller-liveness.md`; `honda-post-setup-integration-contract.md` | `HONDA_CONFIRMED` |
| Creating/appending/setting values invokes configured retain/release callbacks. Exact ownership for every project-created child entry through a post-Setup callout is not dynamically tested; do not generalize Apple ownership rules into Honda proof. | `honda-post-setup-caller-liveness.md`; `honda-cf-callback-ownership.md` | `UNRESOLVED` for a project callout |
| A project-owned append or array replacement at the serializer seam is safe under runtime concurrency and failure semantics. | No runtime validation; caller-side mutability is a static candidate only. | `UNRESOLVED` |
| Honda recognizes Type111 or accepts `{type:111,dataPort:P}`. | Existing Type111 schema is not Honda-confirmed. | `UNRESOLVED` |

The synchronous interval and local serializer predicate (`r0 == 0xc8 && *statusOut == 0`) establish local serialization/body-install success only. They do not establish phone receipt, Type111 acceptance, or an executable hook ABI. The preserved evidence distinguishes mutability during Honda's own Setup from arbitrary project mutation afterward.

See the [bridge contract](honda-cf-bridge-contract.md), [response seam evidence](honda-post-setup-response-seam.md), and [43T1-PREP2 report](../../step-reports/43t1-prep2-offline-runtime-integration-readiness.md).
