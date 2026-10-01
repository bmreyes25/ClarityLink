# Step 43B — Honda Screen property sources and descriptor xrefs

**Date:** 2026-09-30
**Scope:** offline static analysis of the hash-matched Honda `jmcs` ELF and preserved symbol/disassembly/DWARF artifacts. No vehicle, ADB, runtime execution, binary modification, or Type111 implementation.

## Decision summary

The `/info` descriptor is constructed from one `ScreenCopyMain()` result. `ScreenCopyMain` chooses the first registered Screen (`gScreenArray[0]`) under a lock and retains it; if the registry has no first entry, it creates/registers the default main Screen. `AirPlayReceiverSessionScreen_CopyDisplaysInfo` calls it once and copies eight properties into one dictionary. Geometry and max-FPS values flow through configuration-backed globals into the Screen object; `features` is a configured global/bitfield; `uuid` has a generated/default candidate in `ScreenCreate`, but the advertised property source and stability were not conclusively resolved.

The `displays` property handler wraps the one dictionary in a mutable array and appends once. This makes a second element mechanically representable at the collection boundary, but no alternate descriptor source or Honda second-display construction path was established. `forceKeyFrame`/`forceKeyFrameNeeded` appear in literals, and DWARF contains a function name, but the available disassembly does not establish their command semantics or any second-display relationship.

## Input identity and tools

| Check | Result |
|---|---|
| Honda ELF | `extracted/system/system/bin/jmcs` |
| SHA-256 | `cbc7ba881648fb8ffdfcc4c1100a028345c37134a2ae3b9dff7d76572851c232` |
| Second copy | `extracted/system-vendor/system/bin/jmcs`, same SHA-256 |
| Format | 32-bit ARM EABI5 shared object; interpreter `/system/bin/linker` |
| Symbols | available in local ELF and preserved `symbols.json`; key function symbols resolve with `nm` |
| DWARF | `file` reports `debug_info`; `dwarfdump` identifies source files and lines |
| Analysis inputs | `research/native/jmcs/disassembly.txt`, `focused-annotated.txt`, `strings.txt`, `symbols.json`; GNU `nm`; Apple `dwarfdump` |

The ELF was not executed. No ELF, disassembly database, or firmware artifact was added or changed.

## ScreenCopyMain and CopyDisplaysInfo xrefs

| Function | Caller/callee | Address | Role | Second-descriptor implication | Confidence |
|---|---|---:|---|---|---|
| `AirPlayReceiverSessionPlatformCopyProperty` | calls `AirPlayReceiverSessionScreen_CopyDisplaysInfo` | `0x28d328` property branch (Step 32 evidence) | Creates mutable displays CFArray and appends returned dictionary once | Container can hold more values in principle; this branch appends one | High for recorded path |
| `AirPlayReceiverSessionScreen_CopyDisplaysInfo` | calls `ScreenCopyMain` | call `0x287b0c`; function starts `0x287ae0` | Copies eight keys from one main Screen into one mutable dictionary | No loop or count branch in function | High |
| `AirPlayReceiverSessionScreen_StartSession` | calls `ScreenCopyMain` | call `0x2883e0` | Retrieves the main Screen during existing stream start/session initialization | Confirms helper serves more than descriptor serialization; not a second-display path | High |
| `ScreenCopyMain` | calls `ScreenCreate` when no first Screen is available | call `0x2a184e`; helper starts `0x2a17fc` | Selects/retains array index zero, else creates/registers default Screen | No index parameter or enumeration loop | High |
| `ScreenCreate` | called by `ScreenCopyMain`; also exposes property-dictionary input | `0x2a1500` | Initializes Screen state and consumes optional property dictionary | Reusable object initializer exists, but no second descriptor caller found | High for function shape |

A text xref scan of preserved disassembly finds the two `ScreenCopyMain` call sites above. The `CopyDisplaysInfo` local body contains exactly one call and no loop. No call to it outside the displays property path was found in the preserved relevant call/dataflow notes. A whole-binary structural search for every dictionary-producing function/table is not complete; therefore `PARALLEL_DESCRIPTOR_SOURCE` is `INCONCLUSIVE`, not a universal `NOT FOUND`.

## Property source trace

Detailed keys, source kind, evidence addresses, and confidence are in [the property-source table](../research/carplay/honda-screencopymain-property-sources.md). Key conclusions:

- `maxFPS`: Screen property sourced from `g_screen_max_fps`; `screen_add_props` reads `CarPlay/ScreenProperties/MAX_FPS`.
- Pixel dimensions: Screen properties sourced from `g_video_width`/`g_video_height`; configuration keys are `CarPlay/ScreenProperties/VIDEO_WIDTH_PIXELS` and `VIDEO_HEIGHT_PIXELS`.
- Physical dimensions: Screen properties sourced from `g_screen_width`/`g_screen_height`; keys are `System/Display/WIDTH_MILLIMETER` and `HEIGHT_MILLIMETER`. These are config sources, not recovered live values.
- `features`: read from the Screen property seeded through `g_screen_features`; screen feature initialization reads `TOUCH_MODE` and applies bit updates. Exact advertised value and bit meaning are unresolved.
- `edid`: copied object property; backing bytes/object source not resolved.
- `uuid`: numeric CF value in this descriptor; `ScreenCreate` has a 16-byte UUID local and a generated/default path, but the exact advertised source and stability are unresolved.

## Role, UUID, features, and EDID

- **Display role:** no explicit display `type`/role insertion was found in this descriptor. `ScreenCopyMain` and `gMainScreen` establish “main” within this implementation path, not a phone-facing role field. Result: `NOT FOUND` in recovered descriptor path.
- **UUID:** property insertion is confirmed; generation/default origin is an indirect candidate. No relationship to Setup `streamConnectionID` or Type-110 crypto was recovered. Result: UUID-to-stream binding `NOT FOUND` in analyzed dataflow; meaning otherwise unknown.
- **Features:** field construction/source family confirmed; its exact integer and semantics are unknown. No AltScreen hint proved.
- **EDID:** field construction confirmed; no alternate EDID table/source proved.

## `forceKeyFrame` trace

The string table contains `forceKeyFrameNeeded` (`0x337352`, `0x3379fb`) and `forceKeyFrame` (`0x33737b`). DWARF identifies `AirPlayReceiverSessionForceKeyFrame` in `AirPlayReceiverSession.c` around source line 2792, but its emitted low-PC is zero in the available DWARF record and no corresponding function body/xref is present in the preserved disassembly extracts. The nearby string context includes generic session/stream fields (`sessionDied`, `status`, `streams`, `timelineOffset`, `type`); another occurrence is near screen-frame property strings. This is insufficient to decide whether the key is a request/response property, internal refresh state, or UI command. There is no proven relation to opcode 3, ViewArea, or Type111.

Classification: `FORCEKEYFRAME_SEMANTICS=UNKNOWN`; `TYPE111_RELATION=NOT FOUND` in recovered evidence, not proof of semantic absence. Next audit must recover the function body and caller/property consumer before assigning meaning.

## Bounded second-descriptor hypothesis

**HYPOTHESIS:** Honda's mutable `displays` array could carry another descriptor at a collection level, but the current producer is a one-Screen projection. The property sources are reusable only as values for the existing main Screen; no target-specific cluster geometry, distinct UUID, EDID, display role/type, or view-area source is established. A second descriptor is mechanically `PLAUSIBLE` as a data-structure operation, not implementation-ready. Copying the primary descriptor or changing its fields would be unsupported and could alter stock behavior.

## Decision gate

```text
HONDA ELF: FOUND
HASH MATCH: PASS
SCREENCOPYMAIN TRACE: COMPLETE (for recovered helper path)
COPYDISPLAYSINFO TRACE: COMPLETE
PARALLEL DESCRIPTOR SOURCE: INCONCLUSIVE
DISPLAY ROLE SOURCE: NOT FOUND (in recovered phone-facing builder)
UUID SOURCE: INDIRECT_CANDIDATE
UUID TO STREAM BINDING: NOT FOUND (in analyzed dataflow)
FEATURES FIELD: CONFIRMED
EDID FIELD: CONFIRMED
FORCEKEYFRAME SEMANTICS: UNKNOWN
TYPE111 RELATION: NOT FOUND (in recovered evidence)
SECOND DESCRIPTOR MECHANICAL FEASIBILITY: PLAUSIBLE
IMPLEMENTATION READY: NO
LIVE TEST READY: NO
JMCS INTEGRATION READY: NO
EXTERNALDISPLAY LIVE RENDER READY: NO
LD_PRELOAD: PARKED
NEXT STATIC QUESTION: What is the complete code body and caller/consumer dataflow for AirPlayReceiverSessionForceKeyFrame and the forceKeyFrame/forceKeyFrameNeeded properties?
```

## Validation

No model/code changes were justified. Validation completed: `tools/run_tests.sh` reported 224 passed and 4 skipped; self-locator smoke reported 3 passed; all configured simulator JavaScript checks passed; 17 relative Markdown links across the changed research/report files resolved; `git diff --check` passed. No proprietary artifacts were added.
