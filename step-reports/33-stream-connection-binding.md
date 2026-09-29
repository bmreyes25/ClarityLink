# Step 33 — resolve display ↔ stream connection binding

**Date:** 2026-09-29  
**Starting commit:** `1dfe8d8`  
**Scope:** offline static analysis of the exact acquisition `jmcs`; no vehicle, ADB, ptrace, firmware patch, hook, Type-111 implementation, or decoder work.

## Result

The Type-110 request ID is now traced into Honda's screen cryptographic setup. In the inlined `_ScreenSetup` body in `AirPlayReceiverSessionSetup` (`0x2854e0`), Honda reads `streamConnectionID` from the current request stream dictionary via `CFDictionaryGetInt64`. DWARF names the value `streamConnectionID` and types it `uint64_t`. A zero value takes the error/cleanup path.

The 64-bit value is passed to `AirPlay_DeriveAESKeySHA512ForScreen` (`0x288d18`) as the parameter DWARF names `inScreenStreamConnectionID`. The same call also receives the receiver session master-key buffer and length 16. Honda installs the returned AES key/IV through `AirPlayReceiverSessionScreen_SetSecurityInfo` (`0x287d28`), clears temporary key/IV storage, and opens a TCP listener on an ephemeral port. The response builder appends an entry with `type=110` and the allocated `dataPort` (`0x28614a–0x286168`).

This confirms request-ID-to-screen-crypto binding. It does **not** establish that the ID is retained in a named long-lived struct field, that the accept loop maps the socket back to that ID, or that the ID selects the `/info` display UUID. The separate screen setup function writes a 64-bit lookup result at object offsets `+0x10/+0x14`, but its dictionary key is not proven to be `streamConnectionID`.

The display `uuid` remains sourced from a numeric property on `ScreenCopyMain()` and is inserted into the `/info` display dictionary with `CFDictionarySetInt64`. No UUID read/copy/match was found in the analyzed Type-110 flow. No structure containing both display UUID and streamConnectionID was found. Thus the central display-to-stream link remains UNKNOWN.

## Decision gate

```text
STREAMCONNECTIONID REQUEST KEY: "streamConnectionID"; integer read, uint64_t, Type-110 path
INSCREENSTREAMCONNECTIONID: uint64_t argument to AirPlay_DeriveAESKeySHA512ForScreen; direct value flow from request ID
REQUEST_TO_SESSION BINDING: PARTIAL — request ID reaches per-screen crypto; persistent ID storage/accepted-socket mapping unknown
CONNECTION_ID SECURITY ROLE: CONFIRMED — input to screen AES key/IV derivation
DISPLAY UUID ROLE: Phone-facing numeric descriptor property from ScreenCopyMain; no Setup use found
DISPLAY_TO_STREAM BINDING: UNKNOWN — no UUID/ID association found
TYPE110 FULL FLOW: request uint64 ID -> screen key/IV derivation -> SetSecurityInfo -> ephemeral TCP listener -> response {type:110,dataPort:Y}
TYPE111 REQUEST SCHEMA: UNKNOWN; type=111 is prior-art convention; connection ID likely but unproven for Honda
TYPE111 RESPONSE SCHEMA: UNKNOWN; analogous {type:111,dataPort} is a sketch, not Honda evidence
ALTSCREEN FEATURE TOKEN REQUIRED: UNKNOWN — current prior-art is not version-history proof
CONTROL PLANE REQUIRED BEFORE TYPE111: UNKNOWN
PARTIAL STOCK SETUP DELEGATION: UNKNOWN — per-entry loop makes it plausible; rollback/error semantics unresolved
SERVER INFO AUGMENTOR READY: YES, as an offline boundary/model only; Display-B values and runtime ABI are not ready
TYPE111 MODEL READY: NO, complete request/security/response contract not established
LIVE NEGOTIATION TEST READY: NO
BIGGEST BLOCKER: no Honda evidence maps an advertised display UUID/role to a later streamConnectionID/Type-111 request
```

## Readiness and next action

The available evidence supports an offline server-info augmentation model that preserves the existing main entry and treats the outer dictionary/array as mutable. It does not support concrete secondary-descriptor values or a complete Type-111 handler model. The next concrete task is to recover the backing type/stability of the Screen `uuid` property and trace the accepted TCP socket's listener/session owner, while separately reviewing prior-art history for versioned Type-111 schema and token requirements.

No tests were run because this milestone changed research documentation only and added no structured/code models. `git diff --check` is run before commit.

Public prior-art reviewed as context only: [MHI2 AltScreen project](https://github.com/harman-f/mhi2_altscreen_carplay) describes Type-111, stream-generation, and separate control/UI concerns; [xcertplay AirPlay info builder](https://github.com/shilapi/xcertplay/blob/master/shared/src/main/java/com/shilapi/xcertplay/airplay/AirPlayInfoPlist.kt) demonstrates one receiver's 110/111 display convention. Neither source establishes Honda behavior or a version-independent feature-token requirement.
