# Step 26 — Honda CarPlay SETUP response ABI (offline)

**Date:** 2026-09-29
**Starting commit:** `ecf57ba`
**Scope:** local ignored Honda `jmcs` ELF and tracked configuration/research. No vehicle, ADB, ptrace, firmware changes, interposer implementation, or live negotiation.

## Evidence recovered

From `extracted/system-vendor/system/bin/jmcs` (SHA-256 in `research/carplay/jmcs-address-map.md`):

- `AirPlayReceiverSessionSetup` at `0x2854e0` creates a mutable CF-style dictionary at `0x28557e`.
- It creates a TCP listener via `ServerSocketOpen` at `0x28611e`, requesting port 0; the assigned port is returned in a stack output at `sp+0x68`.
- It builds a mutable stream dictionary at `0x286086`, inserts integer `110` under `type` at `0x286152`, and the assigned listener port under `dataPort` at `0x286160`.
- `_AddResponseStream` at `0x284db8` obtains/creates `streams` as a mutable CFArray and appends the stream dictionary. This is an actual Honda array/list representation for stream response entries.
- Setup publishes its response dictionary through an output pointer at `0x286260`. Its separate completion callback at `0x2862b0` receives status/context, not the response dictionary.
- `AirPlayReceiverSessionScreen_CopyDisplaysInfo` at `0x287ae0` separately creates and returns one dictionary after a single `ScreenCopyMain` call (`0x287b0c`). It does not iterate screens or append descriptors.
- `_requestSendPlistResponse` at `0x289f60` is a generic HTTP helper: `CFPropertyListCreateData` → `CFData` bytes/length → `HTTPMessageSetBody`, then release. A call edge from the CarPlay Setup delegate to this helper is not proven.
- `AirPlayReceiverSessionSetup` returns `OSStatus`; available DWARF lacks formal parameter DIEs. Disassembly indicates ARM EABI argument registers and an output pointer, but exact public prototype, caller, thread, and retain/release contract are incomplete.
- Setup also derives AES key material (`AirPlay_DeriveAESKeySHA512ForScreen` at `0x288d18`) and initializes the screen session AES-CTR state through `AirPlayReceiverSessionScreen_SetSecurityInfo` (`0x287d28`). Whether a separate stream may reuse this context or requires independent setup is unknown.

## Evidence labels and field distinction

| Item | Result | Label |
|---|---|---|
| Main display source | `gMainScreen`, `ScreenCopyMain`, index 0 | **HONDA CONFIRMED** |
| Display builder result | one CF-style dictionary | **HONDA CONFIRMED** |
| Display property names and protocol mapping | opaque/partly unresolved | **UNKNOWN** |
| Local 800×480 / 30 FPS / hifi touch | Honda config only; phone-facing field mapping unproven | **HONDA CONFIRMED local / UNKNOWN wire** |
| 153×92 mm | local `System/Display` config; consumption by display builder unproven | **HONDA CONFIRMED local / UNKNOWN wire** |
| Setup stream container | `streams` CFArray | **HONDA CONFIRMED** |
| Stock stream entry | `type=110`, `dataPort=<dynamic port>` | **HONDA CONFIRMED** |
| Primary UUID | source, value, lifetime, persistence unknown | **UNKNOWN** |
| `altScreen` token/features container | no Honda feature container recovered | **UNKNOWN** |
| Type 111 on Honda | not recovered; only open prior art | **PRIOR-ART ANALOG** |
| Distinct secondary UUID/port | fixture invariant only, not Honda runtime evidence | **UNKNOWN on Honda** |

## 24-part decision summary

1. **Trace Setup:** request dictionary → mutable Setup response → per-stream dictionary → `streams` array → output pointer to caller. A separate completion callback receives status/context. The caller's serializer and transport return path remain unresolved.
2. **Containers:** request and response are local CF-style dictionaries; stream entries are CF-style dictionaries; `streams` is CFArray. CF-style property-list routines are present. Binary plist is used in a generic HTTP helper, not proven for this response.
3. **Descriptor fields:** only opaque numeric/object fields inserted by `CopyDisplaysInfo` are established; UUID and named dimensions/features are unknown.
4. **Config versus wire:** dimensions/FPS/touch/physical size are local config; insertion as named phone-facing fields is unknown.
5. **Collections:** display builder returns one dictionary; Setup response uses an array for streams. Multiple stream entries are structurally supported by helper; multiple display descriptors are not established.
6. **ScreenCopyMain:** obtains local main/index 0. It is a convenience main-screen helper used once by descriptor builder. One Honda main screen is initialized; additional object feasibility in generic registry is not equivalent to descriptor iteration.
7. **Primary stream type:** numeric `110` explicitly inserted under `type` in stock stream response (**HONDA CONFIRMED**); its relation to “main” aligns with open prior art (**PRIOR-ART ANALOG**).
8. **Data port:** per-stream `dataPort`, signed numeric via `CFDictionarySetInt64`, assigned by bind port 0/getsockname; Setup caller is Honda-confirmed.
9. **Wire boundary:** callback receives response-like dictionary; final phone-facing serialization and network write are unknown. Field meaning as advertised stream port is high confidence from placement, not wire proven.
10. **Serializer:** generic `_requestSendPlistResponse` exists, but Setup delegate relation is unknown; no safe pre-serialization mutation point proven.
11. **Hook:** stock Setup output is most promising conceptual location; all candidates remain unsafe/unproven pending delegate and ownership recovery. `CopyDisplaysInfo` is poor fit; `_AddResponseStream` is structurally natural but internal ABI and request gating need recovery.
12. **ABI:** ARM EABI/Thumb, OSStatus return in r0, probable session/request/output argument roles from disassembly; formal declaration, ownership, error contract, thread context unknown.
13. **Ownership:** Setup local cleanup uses CFRelease; `_AddResponseStream` releases its local CFArray after inserting it. Caller/output/delegate lifetime rules and safe append semantics remain unknown.
14. **Second descriptor:** unknown; no display descriptor array shown. Stream response entries can be appended structurally, which is a different container.
15. **AltScreen capability:** unknown; no Honda feature container identified.
16. **Type 111:** integer representable in a CF dictionary in general; correct Honda schema and phone acceptance unknown.
17. **UUID:** primary UUID source/lifetime/persistence unknown; secondary uniqueness is conceptually feasible but not established for Honda state.
18. **Dual ports:** stream entries structurally support individual `dataPort` values. Honda dual-listener/dual-port behavior remains unknown.
19. **Security:** Setup derives SHA-512-based AES key material and initializes AES-CTR for the screen session. Secondary stream's independent/reused context requirements unknown.
20. **Framing:** Honda accepted-socket framing parser is only partially recovered; callback length framing is distinct from TCP header. Parser reuse for a separate ClarityLink stream is unknown.
21–22. **Fixture/tests:** created structured JSON with explicitly synthetic UUID/port tokens and tests for preservation/uniqueness/removal; these test model invariants only.
23. **Before live hook:** recover Setup caller/delegate implementation, exact out-object ownership, serializer/write chain, display schema, secondary security and listener ordering.

## GO / NO-GO

```text
HONDA SETUP RESPONSE TYPE: mutable CF-style dictionary with streams CFArray
DISPLAY COLLECTION: CopyDisplaysInfo returns one dictionary; no display array proven
PRIMARY DISPLAY SERIALIZED: PARTIAL (local display dictionary proven; wire serializer unknown)
PRIMARY DATAPORT FIELD: per-stream dataPort signed numeric value in stock type=110 entry
MULTIPLE DISPLAY ENTRIES REPRESENTABLE: UNKNOWN
SECONDARY UUID REPRESENTABLE: UNKNOWN
SECONDARY STREAM TYPE REPRESENTABLE: UNKNOWN (integer field structurally present; Type 111 is prior-art only)
DUAL DATAPORT REPRESENTABLE: UNKNOWN for Honda operation; response list structure can hold multiple port-bearing entries
RESPONSE MUTABLE PRE-SERIALIZATION: YES locally; hook-visible serializer boundary unknown
BEST HOOK POINT: none yet; post-Setup output/delegate boundary is leading candidate
STOCK-DELEGATING HOOK FEASIBLE: UNKNOWN
PRIMARY PATH CAN REMAIN UNCHANGED: UNKNOWN pending hook/phone acceptance
READY FOR DISPLAY-B NEGOTIATION CODE: NO
BIGGEST BLOCKER: untraced Setup response out-pointer caller-to-phone serializer/write edge and response ownership ABI
```

## Fixture and preservation checks

The offline fixture uses clearly marked synthetic IDs/ports so inequality tests do not fabricate recovered Honda values. The exact stock primary fixture entry is preserved in the augmented model; removing the appended entry restores the stock fixture exactly. See `research/carplay/display-b-fixture.md`.

## Next action

Trace the caller consuming Setup's response out-parameter through the exact serializer and phone-facing send, recovering the formal signature and ownership before selecting any hook point. Keep the registry investigation fallback-only.
