# Step 30 — close AltScreen negotiation loop

**Date:** 2026-09-29
**Starting commit:** 71bf150 — ClarityLink: resolve display caller and stream type parser
**Scope:** offline static analysis only. No vehicle, ADB, ptrace, hooks, firmware modification, decoder, or rendering work.

## Identity and method

Analyzed the supplied extracted/system/system/bin/jmcs ELF. SHA-256:

cbc7ba881648fb8ffdfcc4c1100a028345c37134a2ae3b9dff7d76572851c232

The binary is ELF32 little-endian ARM EABI5, not stripped, with symbols and DWARF. Addresses below are ELF VAs; the established VA/file-offset mapping applies to these locations. llvm-objdump disassembly and DWARF were used for the relevant function contracts and data/control flow.

## Server-info builder and displays

DWARF declares:

```c
CFLDictionaryRef AirPlayCopyServerInfo(
    AirPlayReceiverSessionRef inSession,
    CFLArrayRef inProperties,
    uint8_t *inMACAddr,
    OSStatus *outErr);
```

Function VA 0x282cd4; declaration at AirPlayReceiverServer.c:156. It creates/populates a mutable CF dictionary and returns it; outErr is optional. At 0x282e34, it calls AirPlayReceiverSessionPlatformCopyProperty with the session and key "displays". On a non-null result, CFDictionarySetValue inserts the same object under "displays" at 0x282e42, and releases its temporary reference at 0x282e48.

AirPlayReceiverSessionPlatformCopyProperty at 0x28d328 compares the key at 0x28d332–0x28d342; the displays branch creates a CFMutableArray, calls AirPlayReceiverSessionScreen_CopyDisplaysInfo (0x287ae0), appends its main-display dictionary, and returns the array. This closes the local value edge:

```text
CopyDisplaysInfo -> one main descriptor -> mutable displays array
 -> AirPlayCopyServerInfo["displays"] -> returned server-info dictionary
```

It does not close the network edge. No direct caller of AirPlayCopyServerInfo was recovered in the complete available disassembly, and no indirect function-pointer/relocation consumer was established. The triggering request, request path, network/control handler, server-info serializer, response body, and send function remain unknown. The binary-plist serializer and writev path previously proven for _connectionHandleMessage applies to the AirPlayReceiverSessionSetup output object only. It cannot be attributed to server info.

Ownership supports local mutation: server info is created mutable; displays is created mutable; main descriptor is mutable. Builder inserts the owned copied property then releases its temporary reference. No pre-serialization mutation window can be identified until a phone-facing consumer is found.

## Main descriptor and feature field

The established builder fields are edid, features, maxFPS, widthPhysical, heightPhysical, widthPixels, heightPixels, and uuid. Runtime values, complete field semantics, units, and wire visibility are not proven by this send-path trace. The uuid insertion uses a numeric CF setter, so its wire/type representation must remain unknown. features derives from g_screen_features and uses mask logic, but semantic bit names are not recovered. Do not invent meanings.

## SETUP stream parser and Type 111

AirPlayReceiverSessionSetup (0x2854e0) iterates the streams array and extracts each type as an integer through CFDictionaryGetInt64 at 0x28590e. Confirmed cases: 100/101 audio and 110 screen setup (AirPlayReceiverSessionScreen_Setup call at 0x28609c). Type 111 goes to the invalid-type path beginning at 0x2861f6.

The exact externally visible error/status and complete pre-failure side effects remain unresolved. In a multi-entry array, previous entries may already have effects; this was not exhaustively proven. A conceptual Type-111-only diversion immediately at the per-entry dispatch could leave accepted stock cases 100/101/110 delegated to Honda. Neither its live ABI nor safe hook mechanics are validated.

Type 110's response entry is confirmed as type=110 plus dynamically assigned dataPort; Setup's response object reaches the existing binary-plist HTTP response path. No copied request UUID, streamID, or streamConnectionID was established. The relationship between the display UUID and a requested stream remains unknown. Prior-art implementations use separate display descriptors and 110/111 conventions, but they do not prove Honda's missing binding or request-trigger sequence.

## Requested decision gate

```text
AIRPLAYCOPY_SERVERINFO:
  0x282cd4; DWARF signature returns CFLDictionaryRef; inSession, inProperties,
  inMACAddr, optional outErr
SERVER_INFO_PHONE_FACING:
  UNKNOWN
DISPLAYS_PHONE_FACING:
  UNKNOWN
DISPLAYS_CONTAINER:
  MUTABLE (CFMutableArray); enclosing server-info dictionary mutable
CAPABILITY_MUTATION_POINT:
  UNKNOWN; no proven server-info consumer/serializer boundary
PRIMARY_DISPLAY_DESCRIPTOR:
  local main dictionary fields edid, features, maxFPS, width/height physical,
  width/height pixels, uuid; semantics/wire representation partly unknown
DISPLAY_UUID_FLOW:
  main screen property -> numeric CF setter in local descriptor -> displays array
  -> server-info dictionary; no Setup correlation found
FEATURES:
  numeric masked g_screen_features-derived value; bit semantics unknown
TYPE111_REJECTION:
  AirPlayReceiverSessionSetup dispatch -> invalid type branch beginning 0x2861f6
TYPE111_ERROR:
  invalid-type path; exact external status/error mapping unknown
TYPE111_INTERCEPT_POINT:
  conceptual per-entry type dispatch before stock accepted-type/default handling;
  not a validated hook
TYPE110_RESPONSE_TEMPLATE:
  response stream dictionary has type=110 and dynamic dataPort
DISPLAY_STREAM_BINDING:
  UNKNOWN
SECOND_DISPLAY_ADVERTISEMENT_SUFFICIENT:
  UNKNOWN
TWO_HOOK_ARCHITECTURE_SUFFICIENT:
  UNKNOWN
PRIMARY_PATH_PRESERVABLE:
  UNKNOWN (structurally plausible; not proven)
OFFLINE_NEGOTIATION_IMPLEMENTATION_READY:
  NO
LIVE_NEGOTIATION_TEST_READY:
  NO
BIGGEST BLOCKER:
  no recovered caller/serializer/send path proving AirPlayCopyServerInfo reaches
  the phone, plus unknown display-to-stream selection/correlation
```

## Architecture and preservation

The evidence supports a candidate two-hook design only. Hook A has no proven phone-facing boundary. Hook B has an identifiable Type dispatch but not a validated interception ABI, response ownership contract, or secondary stream schema. The exact conditions for preserving 100/101/110 plus primary listener/dataPort, main descriptor/UUID, decoder, center display, audio, and normal lifecycle are not yet established. Therefore two-hook sufficiency and primary-path preservation are UNKNOWN, not YES.

Offline implementation of an interoperable augmentor/Type-111 handler is NO. A local data-structure sketch is possible but would encode unproven schema and should not be represented as negotiation-ready. A future live test is NO until the phone-facing advertisement and stream-binding path are understood. No experiment was performed.

## Deliverables and verification

Added focused server-info, capability-send-path, Type-111 rejection, and response-model notes; updated display capability, UUID, parser, architecture, interposer, project state, evidence index, and next action records. No models or product code changed, so tests were not run. git diff --check is required before commit.

**Next action:** recover every direct and indirect consumer of AirPlayCopyServerInfo, then follow the returned dictionary to the actual response serializer and network send. Keep work offline.
