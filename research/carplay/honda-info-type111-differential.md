# Honda `/info` Type111 descriptor differential

**Audit date:** 2026-09-30
**Scope:** offline review of the preserved Honda `jmcs` ELF and source-pinned xcertplay. No vehicle, ADB, Honda runtime, firmware modification, Type111 implementation, or live test.

## Evidence classes and decision rule

- `HONDA_CONFIRMED`: exact Honda artifact dataflow shows the key being constructed/serialized in the phone-facing `/info` object.
- `HONDA_INDIRECT_CANDIDATE`: a related Honda symbol, helper, literal, or structure exists, but its role in the display descriptor or `/info` contract is not proven.
- `HONDA_ABSENT_LITERAL`: exact key/command literal was not found in the inspected Honda ELF or recovered descriptor builder. This only describes literal evidence; it does not prove semantic absence.
- `HONDA_UNKNOWN`: available evidence does not decide the question.
- `EXTERNAL_PRIOR_ART`: behavior in the pinned xcertplay implementation; not Honda evidence.
- `HYPOTHESIS`: bounded design inference to test with Honda evidence.

Honda binary reviewed: `extracted/system/system/bin/jmcs`, SHA-256 `cbc7ba881648fb8ffdfcc4c1100a028345c37134a2ae3b9dff7d76572851c232`. The preserved `system-vendor/system/bin/jmcs` copy has the same SHA-256. Exact literal checks used the host `strings -a` output against this ELF; analysis is static and the binary was not executed. Step 43B traces the descriptor property sources and confirms one `ScreenCopyMain()` object feeds the recovered builder; see [property-source trace](honda-screencopymain-property-sources.md).

## Source-pinned xcertplay behavior (`EXTERNAL_PRIOR_ART`)

Repository commit: [`de9647f4bdfb1be356bed4cac0519400473712a6`](https://github.com/shilapi/xcertplay/commit/de9647f4bdfb1be356bed4cac0519400473712a6). Inspected source: [`AirPlayInfoPlist.kt`](https://github.com/shilapi/xcertplay/blob/de9647f4bdfb1be356bed4cac0519400473712a6/shared/src/main/java/com/shilapi/xcertplay/airplay/AirPlayInfoPlist.kt), especially `build` lines 24–72, `displayEntry` lines 141–166, and `areaDict` lines 168–189. This source explicitly says the phone reads `/info` before requesting streams.

| Field | Main display | Cluster display | Source behavior |
|---|---|---|---|
| `type` | constant 110 | constant 111 | Added as a per-entry argument to the shared builder. |
| `uuid` | configured constant `MAIN_UUID` | different configured constant `ALT_UUID` | Both are strings in this source; cluster identity is distinct. |
| `maxFPS` | sanitized `config.main.fps` | sanitized cluster config FPS | Per-display value. |
| `widthPixels`, `heightPixels` | `config.main` | cluster config | Per-display dimensions. |
| `widthPhysical`, `heightPhysical` | sanitized config/default physical mm | sanitized cluster config/default physical mm | Height can be estimated from aspect ratio if omitted. |
| `features` | shared builder bitmask `0x08 \| 0x02` | same bitmask | xcertplay's named bits are touch/knob features; not a universal protocol definition. |
| `primaryInputDevice` | display config value | cluster display config value | Emitted on each entry; values are configuration-dependent. |
| `viewAreas` | one generated area | one generated area | Always inserted by this builder; area geometry derives from each display config. |
| `initialViewArea` | integer 0 | integer 0 | Always inserted by this builder. |
| `initialURL` | only when configured | only when configured | Conditional; not necessarily emitted in every profile. |
| `safeArea` | nested in the area's dictionary | nested in the cluster area's dictionary | Always created by `areaDict`; explicit insets or full-display defaults. |

The xcertplay builder appends the cluster entry only when `config.cluster` is non-null. These findings verify what this pinned implementation emits, not mandatory fields in Apple's protocol or Honda's implementation.

## Honda phone-facing `/info` dataflow (`HONDA_CONFIRMED`)

Current path recovered in [Step 32](../../step-reports/32-airplay-info-phone-path.md):

```text
_connectionHandleMessage /info route (0x28b678–0x28b68e)
  -> _requestProcessInfo (0x28a018)
  -> AirPlayCopyServerInfo (0x282cd4; call at 0x28a156)
  -> returned serverInfo dictionary passed to _requestSendPlistResponse (0x289f60; call at 0x28a19c)
  -> binary plist serialization
  -> HTTPConnectionSendResponse (0x29dbe4)
  -> SocketWriteData -> writev
```

`serverInfo["displays"]` is the same array produced by the Honda display-property path, inserted into the dictionary, and serialized by this `/info` response. The array is mutable but the current path calls `ScreenCopyMain()` once and appends one descriptor. The phone-facing static dataflow is confirmed; no particular runtime phone exchange was captured in this milestone.

The descriptor builder is `AirPlayReceiverSessionScreen_CopyDisplaysInfo` at VA `0x287ae0`. It creates a mutable dictionary, calls `ScreenCopyMain()` once, copies properties from that main-screen object, and inserts `edid`, `features`, `maxFPS`, `widthPhysical`, `heightPhysical`, `widthPixels`, `heightPixels`, and `uuid`. Numeric fields use numeric CF setters. In particular, `uuid` is inserted as a numeric CF value here; `ScreenCreate` contains a 16-byte UUID local and generated/default path, but the advertised source and stability remain unknown. Step 43B traces geometry/FPS through configuration-backed globals into the Screen object. The property callback at `0x28d328` creates a mutable array and appends this one dictionary. `ScreenCopyMain` reads only `gScreenArray[0]` under lock, retaining it; if absent it creates/registers the default main screen. No loop, alternate index, role key, or parallel source was recovered in the audited path. The outer array is mutable, so a second entry is mechanically representable at the container boundary, but the current producer does not build it. `forceKeyFrame`/`forceKeyFrameNeeded` and the named function remain unresolved: no second-display or ViewArea dataflow was recovered.

## Field-by-field differential

Honda status is scoped to the recovered `/info` descriptor builder plus exact-string checks on the matching Honda ELF. `ABSENT_LITERAL` is deliberately not a behavior-absence claim. Evidence locations below point to current analysis notes; where the exact instruction address is not preserved in the source note, the function address is given rather than invented.

| Field | xcertplay main | xcertplay cluster | Honda status | Honda evidence and confidence | ClarityLink implication / next static question |
|---|---|---|---|---|---|
| `type` | 110 | 111 | `HONDA_INDIRECT_CANDIDATE` | Honda has the literal `type` in Setup stream dictionaries and numeric type dispatch, but no role/type insertion is recovered in `CopyDisplaysInfo`. Low for an `/info` display role. See `honda-copy-displays-info.md`, function `0x287ae0`, and stream type parser notes. | Find any alternate display-type source or encoded enum in `ScreenCopyMain` properties and confirm whether it reaches this dictionary. |
| `uuid` | configured main UUID | distinct configured alternate UUID | `HONDA_CONFIRMED` | Key is inserted from a `ScreenCopyMain()` property using `CFDictionarySetInt64` in `0x287ae0`; `/info` inclusion is confirmed by Step 32. High for field insertion, unknown for identity meaning/value. | Recover backing property type/stability and all consumers; do not equate it with Type111 stream routing. |
| `maxFPS` | sanitized config FPS | sanitized cluster config FPS | `HONDA_CONFIRMED` | Key and numeric insertion from main-screen property in `0x287ae0`; exact value not recovered. High. | Trace source property and configuration provenance/value. |
| `widthPixels` | main config | cluster config | `HONDA_CONFIRMED` | Key and numeric insertion from main-screen property in `0x287ae0`; exact negotiated/runtime value not recovered. High. | Trace source and distinguish panel bounds from cluster navigation region. |
| `heightPixels` | main config | cluster config | `HONDA_CONFIRMED` | Key and numeric insertion from main-screen property in `0x287ae0`; exact value not recovered. High. | Same as width. |
| `widthPhysical` | main config/default | cluster config/default | `HONDA_CONFIRMED` | Key and numeric insertion in `0x287ae0`; units/value not recovered. High for key. | Identify units and property source before proposing geometry. |
| `heightPhysical` | main config/default | cluster config/default | `HONDA_CONFIRMED` | Key and numeric insertion in `0x287ae0`; units/value not recovered. High for key. | Same. |
| `features` | shared display bitmask | same shared display bitmask | `HONDA_CONFIRMED` | Numeric value is read/transformed from `g_screen_features` and inserted by `0x287ae0`; bit semantics/value unresolved. High for construction. | Recover bit provenance/meaning; never infer an AltScreen bit from the integer alone. |
| `primaryInputDevice` | per-display config value | per-display config value | `HONDA_ABSENT_LITERAL` | No such key in the recovered builder or exact ELF string scan. High for literal absence in inspected artifact; dynamic/generated behavior remains possible. | Inspect generic dictionary helpers and any input/HID descriptor path. |
| `viewAreas` | one generated area | one generated area | `HONDA_ABSENT_LITERAL` | No key in recovered builder or exact ELF string scan. High for literal absence only. | Inspect generic serializer/property paths and Setup feature handling; do not infer an area from array-shaped `displays`. |
| `initialViewArea` | 0 | 0 | `HONDA_ABSENT_LITERAL` | No key in recovered builder or exact ELF string scan. High for literal absence only. | Search related numeric selection state and serialized dictionaries. |
| `initialURL` | conditional config value | conditional config value | `HONDA_ABSENT_LITERAL` | No key in recovered builder or exact ELF string scan. High for literal absence only. | Search URL constants/config and generic UI/control paths. |
| `safeArea` | nested area geometry | nested cluster area geometry | `HONDA_ABSENT_LITERAL` | No key in recovered builder or exact ELF string scan. High for literal absence only. | Search coordinate/inset structures and any non-string serialization path. |
| `edid` (Honda-only key) | not emitted by xcertplay's display entry | not emitted | `HONDA_CONFIRMED` | Honda builder inserts `edid` from main-screen object in `0x287ae0`; wire object is part of the `/info` dictionary. High for insertion. | Determine whether it is a nested dictionary/data blob and if it carries display geometry/identity semantics. |
| UUID-to-stream binding | xcertplay uses per-display UUID constants in `/info`; this source does not establish its relation to stream IDs | separate cluster UUID | `HONDA_UNKNOWN` | Honda Step 33/43 finds no UUID read/match in analyzed Type110 Setup and no structure joining UUID to `streamConnectionID`. | Search all recovered Setup and session-property xrefs; keep presentation identity and transport identity distinct unless joined by evidence. |
| Type111 required field set | implementation emits its own configured descriptor | implementation conditionally adds its configured cluster descriptor | `HONDA_UNKNOWN` | Honda has no recovered Type111 descriptor and this source cannot establish Honda/iOS requiredness. | Requires Honda-specific request/response or controlled compatibility evidence after deployment gates. |

### Separate UI/control-plane literal audit

These are not display-entry fields and must not be conflated with `/info` descriptor keys.

| Term | Honda status | Evidence / confidence | Meaning remains open |
|---|---|---|---|
| `suggestUI`, `showUI`, `stopUI` | `HONDA_ABSENT_LITERAL` | Exact jmcs string scan and Step 34; high for literal absence. | Generic platform/session-control paths and mode/UI helper symbols exist, but command semantics are not recovered. |
| `SecondDisplayMode` | `HONDA_ABSENT_LITERAL` | Exact jmcs string scan; high for literal absence. | Whether equivalent mode state is numeric or generic is unknown. |
| `ViewArea`, `ViewAreaChanged` | `HONDA_ABSENT_LITERAL` | Exact jmcs string scan and Step 34; high for literal absence. | No conclusion about implicit geometry or generic control handlers. |
| `forceKeyFrame` | `HONDA_INDIRECT_CANDIDATE` | Exact string occurs in jmcs at file offset `0x33737b`, adjacent to `forceKeyFrameNeeded` (`0x337352`); symbol `AirPlayReceiverSessionForceKeyFrame` exists. Low for any Type111/UI relation. | Recover xrefs and determine whether the string/function is stock video control, a property, or unrelated to a second display. |
| `enabledFeatures`, `altScreen`, `FeatureKey`, `screenFeatures`, `naviScreenInfo` | `HONDA_ABSENT_LITERAL` | Exact jmcs string scan; high for literal absence in this binary. Step 32 separately reports no modern feature-token array construction in recovered response code. | Dynamic/generic/numeric representations are not ruled out. |

The exact ELF string scan found literal `type`, `uuid`, `features`, and geometry keys in the binary. The literal `type` is used in Honda's Setup stream dictionaries, so its relationship to a display descriptor is classified as `HONDA_INDIRECT_CANDIDATE`, not as confirmed `/info` display semantics. For the fields classified absent, only absence of the exact literal was tested; that is not proof the capability or an equivalent encoding is absent.

Reproducible focused scan:

```sh
strings -a -t x extracted/system/system/bin/jmcs | rg -i 'forceKeyFrame|suggestUI|showUI|stopUI|SecondDisplayMode|ViewArea|altScreen|viewAreas|initialViewArea|safeArea|primaryInputDevice|naviScreenInfo|enabledFeatures|FeatureKey|screenFeatures|initialURL|widthPixels|heightPixels|widthPhysical|heightPhysical|maxFPS|uuid|features|edid'
```

## Bounded second-display hypothesis (`HYPOTHESIS`)

No Honda field is proven mandatory for a secondary descriptor because Honda has no recovered Type111 descriptor and xcertplay is one external implementation. A testable *candidate* would preserve the existing main dictionary unchanged, then append one separately identified candidate descriptor to the already-array-shaped `displays` value. Cloning the primary descriptor could be a schema-preserving starting point for analysis, but the candidate's type/role and UUID would need to differ, and display geometry/FPS/input fields would need target-specific provenance; opaque EDID/features must not be copied or modified without understanding them. A distinct UUID is plausible as presentation/capability identity, because that is how xcertplay represents two displays, but Honda's numeric UUID source has no proven relation to Type110 `streamConnectionID` or transport routing.

### Step 43D update — separate capability and stream traces

The Honda Setup trace now confirms the Type-110 stream path more fully: request `type` chooses the screen branch; request `streamConnectionID` is read as a nonzero uint64 and passed into screen key/IV derivation; response `type=110` and the listener-selected `dataPort` are appended. The `/info` builder separately inserts a numeric Screen `uuid`. No direct UUID-to-streamConnectionID reference was recovered. This means the search should first keep display capability identity and Setup stream identity as separate layers; it does **not** establish Honda's UUID as presentation-only or as HID/input identity. Honda semantic role remains `UNKNOWN`. Detailed source-pinned context is in [Step 43D](../../step-reports/43d-setup-stream-identity-correlation.md) and [Setup identity prior art](setup-stream-identity-prior-art.md).

`viewAreas`, `initialViewArea`, and nested `safeArea` are emitted by the pinned xcertplay builder, while `initialURL` is optional there. They are not yet shown to be mandatory across receiver generations. `primaryInputDevice` may be tied to interactive input and could be optional for a cluster map, but that too is unknown. Honda's `features` bit meanings and `edid` structure must be recovered before copying or mutating them. The candidate is not implementation-ready because Type111 triggering requirements, exact iOS response expectations, Honda feature semantics, display identity, capability negotiation, and a safe jmcs integration seam remain unresolved.

## Next bounded Honda static-analysis plan

1. Re-open the exact SHA-256-matched jmcs symbol/disassembly artifacts; anchor every observation to the correct `0x287ae0` builder and `0x28d328` displays-property branch.
2. Trace references to the literal keys listed above into CF string construction and `CFDictionarySetValue`/numeric setter calls. Check for a parallel descriptor builder or table not reached by `ScreenCopyMain()`.
3. Trace `ScreenCopyMain` and `gScreenArray[0]` property sources for `uuid`, `features`, FPS, dimensions, and EDID; follow configuration constants and values around display setup (including the known 800×480 references) without equating unrelated Android canvas settings to `/info` values.
4. Inspect `AirPlayCopyServerInfo` qualifiers and the `_requestProcessInfo` serialization boundary to confirm no qualifier-specific descriptor variant is selected. Keep this scoped to the phone-facing object already proven in Step 32.
5. Follow the xrefs for `forceKeyFrame` / `forceKeyFrameNeeded` and `AirPlayReceiverSessionForceKeyFrame`; do not infer secondary-screen semantics from the symbol name.
6. Revisit generic platform/session-control dictionary parsing for numeric or indirect equivalents of `suggestUI`, `showUI`, `stopUI`, and view-area operations.
7. Record each new key, source property, insertion function/address, and exact serialization reachability. Leave unresolved items `HONDA_UNKNOWN`.

## Source and evidence links

- Honda `/info` phone-facing path and corrected Step 31 conclusion: [Step 32](../../step-reports/32-airplay-info-phone-path.md).
- Honda descriptor construction: [CopyDisplaysInfo recovery](honda-copy-displays-info.md), [UUID flow](honda-display-uuid-flow.md), [capabilities](honda-info-capabilities.md).
- Honda control literal search: [PlatformControl / SessionControl audit](honda-platform-control.md).
- External descriptor source: [pinned xcertplay commit](https://github.com/shilapi/xcertplay/commit/de9647f4bdfb1be356bed4cac0519400473712a6), [`AirPlayInfoPlist.kt`](https://github.com/shilapi/xcertplay/blob/de9647f4bdfb1be356bed4cac0519400473712a6/shared/src/main/java/com/shilapi/xcertplay/airplay/AirPlayInfoPlist.kt).
- Broader external-only context: [CarPlay AltScreen prior art](../../docs/research/carplay-altscreen-prior-art.md).

## Readiness

This audit improves the field-level question but does not make Type111 implementation-ready. Honda `/info` phone-facing delivery and one main descriptor are confirmed; the second-display schema, required fields, type/UUID semantics, Type111 security/stream association, jmcs entry seam, and real renderer handoff remain unresolved. No live gate changes.
