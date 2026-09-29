# Step 34 — separate AltScreen transport and presentation

**Date:** 2026-09-29
**Starting commit:** `c950547`
**Scope:** offline review of the acquired Honda `jmcs` ELF and MHI2 current source pinned at `c2f811f1a5c84dae3a62f4cf9b4a9e65fc3f7b3c`. No vehicle, ADB, ptrace, firmware patch, hook, Type-111 implementation, decoder, or rendering. No live key material was captured or saved.

## Result

Step 33's direct UUID-to-`streamConnectionID` mapping is no longer a primary transport requirement. Honda Type 110 shows `streamConnectionID` as a `uint64` input to stock per-screen key/IV derivation, alongside the receiver session's 16-byte master-key material. The derivation function is not passed the stream type or display UUID. The screen key/IV are installed on the screen-session object. Honda then creates a TCP listener and returns `{type:110,dataPort}`. Honda still rejects 111 before this path, so applying the same primitive to Type 111 is structurally plausible but not Honda-proven.

Honda's accepted fd is wrapped in a per-screen-thread `NetSocket` and used by `ProcessFrames`; listener output and thread context are associated operationally, but exact persistent object-field ownership remains partial. A TCP peer reaching a dedicated listener is bound to that listener's transport generation without a UUID at the media socket layer. Phone-side display selection/correlation is separate and still unknown.

The MHI2 implementation source confirms the split on its target: it observes the stock session security seam, derives screen crypto for the Type-111 connection ID, owns its listener/session, and handles presentation commands through separate control wrappers. It clones unknown peer fields rather than reconstructing an assumed descriptor. In MHI2's model, Type-111 transport may remain live while `suggestUI`, `showUI`/`stopUI`, ViewArea, or provider state changes. This is prior art, not Honda proof.

## Exact Type-110 crypto input conclusion

```text
SCREEN_CRYPTO_INPUTS: receiver session master key (16 bytes), streamConnectionID (uint64)
STREAM_TYPE_IN_CRYPTO: NO — type dispatch happens outside the derivation call
UUID_IN_CRYPTO: not observed
SEPARATE_SESSION_ID_IN_CRYPTO: not observed as a derivation argument; session context supplies master material
```

The screen crypto context is installed on the screen-session object. The accepted native socket is owned by a `NetSocket` wrapper during frame reads. Persistent ID storage and listener/session offsets are incompletely reconciled. No key or IV bytes are included in deliverables.

## MHI2 Type-111 request/response source behavior

At the pinned commit, MHI2 selects the request's type-111 descriptor from `streams`, clones it, derives crypto from its `streamConnectionID` and stock session security material, and constructs a separate listener. Its response clone changes `dataPort` and `streamID=111`; other descriptor fields are preserved. For delegating normal streams, it clones the root request and replaces only `streams` with non-111 entries. This is target-specific: Honda's Type-110 response uses `type=110`, and the correct Honda Type-111 response identity key remains unknown.

## Honda control-plane findings

Honda symbols confirm `AirPlayReceiverSessionPlatformControl`, `AirPlayReceiverSessionControl`, mode-state parsing, and UI/mode helper functions. Exact ELF string search found no `suggestUI`, `showUI`, `stopUI`, `ViewArea`, `altScreen`, `viewAreas`, cluster URLs, or `instrumentcluster` strings. This supports `HONDA_PLATFORMCONTROL=present; command semantics unknown` and `SUGGESTUI/SHOWUI=unknown` rather than concluding those functions are unsupported.

MHI2 demonstrates transport-before-UI-selection in its implementation model. Honda ordering remains unknown. The display UUID is reclassified as presentation/capability identity (possibly other roles), not a proven transport binding or crypto input.

## Type-111 delegation decision

Recommended future shape: wrapper around Setup boundary, clone/split the request so stock receives all normal non-111 entries, preserve root and descriptor fields, then append a response cloned from the exact Type-111 descriptor after stock succeeds. Avoid calling stock with an unsupported Type 111 and trying to repair its failure afterward. This preserves the primary streams by construction, but Honda partial-success/rollback and empty/mixed-array behavior remain unknown; no implementation is ready.

## Decision gate

```text
STREAMCONNECTIONID ROLE: Per-screen crypto derivation input and transport-generation identifier; no display UUID binding shown
CRYPTO INPUTS: 16-byte receiver-session master key + uint64 streamConnectionID
TYPE IN CRYPTO: NO for recovered derivation contract
SOCKET OWNER: Accepted fd is in per-thread NetSocket wrapper during frame processing; listener/session field mapping partial
LISTENER PROVIDES STREAM BINDING: YES at the dedicated network endpoint; persistent Honda object linkage partial
TYPE111 CRYPTO REUSE: UNKNOWN for Honda; same stock primitive is structurally reusable and MHI2 uses it
MHI2 TYPE111 REQUEST FIELDS: cloned request root/streams, select type-111 descriptor, read streamConnectionID; unknown peer fields retained
MHI2 TYPE111 RESPONSE FIELDS: clone requested descriptor; set dataPort and streamID=111; append to preserved response streams
HONDA TYPE111 DELEGATION STRATEGY: stock clone without Type 111, let stock process other entries, then append a cloned Type-111 response; no implementation
DISPLAY UUID ROLE: Presentation/capability identity; no transport/crypto mapping found
HONDA PLATFORMCONTROL: symbol exists; mode/UI helpers exist; exact command semantics unresolved
SUGGESTUI / SHOWUI SUPPORT: UNKNOWN; strings absent from ELF, generic control parsing remains possible
ALTSCREEN TOKEN REQUIREMENT: VERSION-DEPENDENT for modern R15-era tokens; whether Type 111 predates tokens UNKNOWN
TYPE111 TRANSPORT CAN PRECEDE UI CONTROL: YES in MHI2 model; UNKNOWN for Honda
OFFLINE TRANSPORT IMPLEMENTATION READY: NO as executable code; conceptual model only
LIVE TRANSPORT TEST READY: NO
BIGGEST BLOCKER: Honda Type-111 request/response/security contract and safe mixed-stream Setup delegation are not established
```

## Readiness and next action

```text
SERVER INFO AUGMENTOR: READY as offline boundary model only
TYPE111 SETUP MODEL: READY as explicitly hypothetical design, not wire contract
CRYPTO MODEL: PARTIAL; exact Type-110 inputs known, Type-111 compatibility unproven
FRAMER: NOT READY; Honda TCP/record grammar and VideoConfig boundary incomplete
```

Next: recover the Honda screen parser and listener/session ownership from `ProcessFrames` through decrypt and VideoConfig using the exact ELF, then use that contract to design an offline Type-111 wrapper and acceptance criteria. Do not run a vehicle experiment yet.

## Verification

Documentation-only changes; no tests run. `git diff --check` is run before commit.
