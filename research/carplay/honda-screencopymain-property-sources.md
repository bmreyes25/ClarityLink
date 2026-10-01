# Honda `ScreenCopyMain` property sources — Step 43B

**Classification:** Honda static evidence only (`HONDA_CONFIRMED` / `HONDA_UNKNOWN`). No vehicle, ADB, Honda runtime, binary modification, or Type111 implementation was used.

## Input identity and tools

The local source is `extracted/system/system/bin/jmcs`; the matching copy under `extracted/system-vendor/system/bin/jmcs` has the same SHA-256, `cbc7ba881648fb8ffdfcc4c1100a028345c37134a2ae3b9dff7d76572851c232`. The binary is a 32-bit ARM EABI5 ELF and `file` reports it as not stripped with `debug_info`. The generated `research/native/jmcs/symbols.json`, `disassembly.txt`, `focused-annotated.txt`, and `strings.txt` were used with `nm` and Apple `dwarfdump`. Relevant symbols and DWARF source lines are present. No proprietary binary or generated analysis database was added in this milestone.

## Descriptor construction path

```text
_connectionHandleMessage /info
 -> _requestProcessInfo
 -> AirPlayCopyServerInfo
 -> AirPlayReceiverSessionPlatformCopyProperty("displays")
 -> mutable CFArray; append AirPlayReceiverSessionScreen_CopyDisplaysInfo once
 -> mutable dictionary populated from ScreenCopyMain()
 -> binary-plist /info response (Step 32)
```

`AirPlayReceiverSessionScreen_CopyDisplaysInfo` (file offset `0x287ae0`, Thumb VA `0x287ae1`, size `0x248`) calls `ScreenCopyMain` once at `0x287b0c`. It copies one object-valued property (`edid`) and reads/inserts seven numeric properties (`features`, `maxFPS`, physical/pixel dimensions, `uuid`). It has no loop, conditional descriptor count, or array append. `AirPlayReceiverSessionPlatformCopyProperty` wraps the result in a mutable array and appends it once. The actual `/info` phone-facing static flow is established by Step 32; this is not a live phone transaction.

## Property source table

| Key | Insertion site | Value source | Source kind | Value/range | Phone-facing? | Confidence | Alternate-display implication |
|---|---|---|---|---|---|---|---|
| `edid` | `CopyDisplaysInfo` `0x287b2a`–`0x287b40`, `CFObjectCopyProperty` then `CFDictionarySetValue` | `edid` property on returned Screen object | `SCREEN_OBJECT_FIELD` | opaque object; contents not decoded here | Yes, via Step 32 | High for insertion/source object; low for backing data | No second EDID source established |
| `features` | `0x287b4a`–`0x287bb4`, numeric getter, masks, numeric dictionary setter | Screen property populated from `g_screen_features`; feature setup reads `CarPlay/ScreenProperties/TOUCH_MODE` and updates bits | `GLOBAL_CONFIG` | exact transmitted value and bit meanings not established | Yes | High that this is a configured global/property path; semantics unknown | No AltScreen bit established |
| `maxFPS` | `0x287bb8`–`0x287bd8` | Screen property sourced from `g_screen_max_fps`, read from `CarPlay/ScreenProperties/MAX_FPS` in `screen_add_props` | `GLOBAL_CONFIG` | no runtime value recovered | Yes | High for config-key lineage | No distinct secondary FPS setting recovered |
| `widthPixels` | `0x287bde`–`0x287c02` | Screen property sourced from `g_video_width`, populated from `CarPlay/ScreenProperties/VIDEO_WIDTH_PIXELS` | `GLOBAL_CONFIG` | no runtime value recovered | Yes | High for config-key lineage | No separate cluster region value recovered |
| `heightPixels` | `0x287c08`–`0x287c2c` | Screen property sourced from `g_video_height`, populated from `CarPlay/ScreenProperties/VIDEO_HEIGHT_PIXELS` | `GLOBAL_CONFIG` | no runtime value recovered | Yes | High for config-key lineage | No separate cluster region value recovered |
| `widthPhysical` | `0x287c32`–`0x287c56` | Screen property sourced from `g_screen_width`, read from `System/Display/WIDTH_MILLIMETER` | `GLOBAL_CONFIG` | no runtime value recovered | Yes | High for config-key lineage | No second physical width source recovered |
| `heightPhysical` | `0x287c5c`–`0x287c80` | Screen property sourced from `g_screen_height`, read from `System/Display/HEIGHT_MILLIMETER` | `GLOBAL_CONFIG` | no runtime value recovered | Yes | High for config-key lineage | No second physical height source recovered |
| `uuid` | `0x287c86`–`0x287ca6`, copied then numeric dictionary setter | `uuid` property on Screen object; `ScreenCreate` accepts a property dictionary and contains a 16-byte UUID local and a generated/default property path | `DERIVED_RUNTIME_VALUE` / `SCREEN_OBJECT_FIELD` | inserted as numeric CF value here; stability and exact origin unresolved | Yes | High for numeric insertion; medium/low for generation lineage | Display identity candidate only; no transport binding shown |

The screen object is created/seeded by `ScreenCreate` (`0x2a1500`) and configured through `_ScreenSetProperty` (`0x2a13a8`). The reusable property accessors are `_ScreenCopyProperty` (`0x2a16ec`) and `_ScreenSetProperty`; their DWARF source locations identify `Support/ScreenUtils.c`. `screen_add_props` (`0xabd50`) writes the configured display values into `gMainScreen`. This proves property flow into the descriptor, not the contents of private configuration files or runtime values. EDID backing content and UUID stability remain unknown.

## Hidden keys and role

The builder's complete insertion sequence contains only the eight listed keys. It does not insert a display `type`, role, `primaryInputDevice`, view-area, safe-area, or URL field. Exact strings for the xcertplay candidates were checked against this ELF as recorded in Step 43A. Literal absence remains a statement about inspected literals and this function only. `ScreenCopyMain`'s name and registry behavior identify the selected object as the main screen in this code path; no separate phone-facing role field or second-screen identity mechanism was recovered.

`ScreenCopyMain` (`0x2a17fc` entry) locks `gScreenArray`, checks array count, retrieves index 0, and retains the object. When no usable first entry exists, it creates/registers the default Screen. It does not iterate for other displays or choose a role based on a supplied index. That function is called from the recovered `CopyDisplaysInfo` descriptor path once.

## Bounded conclusion (`HYPOTHESIS`)

Appending another dictionary to the outer mutable array is mechanically possible in generic CF terms, but Honda's recovered producer is not a reusable multi-display builder: it gets one main Screen object, serializes its properties into one dictionary, and the displays handler appends that dictionary once. Reusing the primary properties for a cluster descriptor would not establish correct geometry, EDID, UUID, role/type, or feature semantics. A distinct UUID source is not established. Therefore a second descriptor is **mechanically plausible at the container boundary, not implementation-ready**.

## Evidence anchors

- Honda local disassembly: `research/native/jmcs/display-negotiation-excerpt.txt` and `focused-annotated.txt`; function addresses listed above.
- Honda `/info` static dataflow: [Step 32](../../step-reports/32-airplay-info-phone-path.md) and [current server-info path](honda-server-info.md).
- Exact field differential and external-only comparator: [Step 43A differential](honda-info-type111-differential.md).
- Descriptor insertion details: [CopyDisplaysInfo](honda-copy-displays-info.md) and [UUID flow](honda-display-uuid-flow.md).
