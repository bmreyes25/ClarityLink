# Honda primary display descriptor evidence

**Scope:** offline analysis of the local `jmcs` ELF and Honda `j_config.xml`. Local geometry must not be confused with phone-facing descriptor fields.

## Construction point

`AirPlayReceiverSessionScreen_CopyDisplaysInfo` (`jmcs` VA `0x287ae0`) creates one mutable CF-style dictionary, calls `ScreenCopyMain` (`0x2a17fc`) once, reads properties from that single returned main-screen object, and inserts values with `CFDictionarySetInt64` / `CFDictionarySetValue`. There is no screen enumeration loop or CFArray append in this routine. It returns one dictionary through its out parameter. The property-key objects are compiled constants; this report does not assign Apple or prior-art field names where a Honda-side semantic string is not recovered.

| Field / key | Value | Type | Source | Confidence |
|---|---|---|---|---|
| Screen object selected | `ScreenCopyMain()` / registry index 0 | local screen object | `0x287b0c` call | **HONDA CONFIRMED** |
| Dictionary result | one mutable CF-style dictionary | CFDictionary | `0x287af8`, returned via out pointer | **HONDA CONFIRMED** |
| Numeric properties | multiple `CFObjectGetPropertyInt64Sync` values inserted by `CFDictionarySetInt64` | CFNumber/int64-like | `0x287b54` onward | **HONDA CONFIRMED**, individual key semantics partly unresolved |
| Object property | copied property inserted with `CFDictionarySetValue` | CF object | `0x287c98..0x287ca6` | **HONDA CONFIRMED**, semantic field unresolved |
| UUID | no source or insertion identified in this bounded function | unknown | no positive evidence | **UNKNOWN** |
| `widthPixels`, `heightPixels`, physical dimensions, `maxFPS`, features, input, view area, URL | no proven mapping to the opaque Honda keys | unknown | do not map from prior art | **UNKNOWN** |
| `dataPort` | not inserted by this display-info routine | unknown | separate SETUP stream dictionary | **HONDA CONFIRMED** for separation |

## Local configuration versus phone-facing descriptor

| Value | Local Honda configuration | Inserted into phone-facing descriptor? |
|---|---|---|
| 800×480 | configured primary screen | **UNKNOWN**; properties are copied into the local dictionary, but no proven serializer/schema edge names them as pixel dimensions |
| 30 FPS | configured primary screen | **UNKNOWN**; no proven phone-facing field mapping |
| high-fidelity touch | configured primary screen | **UNKNOWN**; protocol mapping not recovered |
| 153×92 mm | local `System/Display` config | **UNKNOWN**; this config item is not proven to be consumed by this descriptor builder |

`ScreenCopyMain` is a convenience accessor to the main registered screen; the descriptor builder uses it as a single-screen assumption. Honda initialization currently evidences one `gMainScreen`. A generic registry array exists, but that does not establish that this builder supports or serializes multiple displays.

## Conclusion

```text
DISPLAY CONTAINER: single returned dictionary in observed Honda builder
MULTIPLE DISPLAY ENTRIES STRUCTURALLY SUPPORTED BY THIS BUILDER: no evidence / UNKNOWN
PRIMARY DISPLAY SERIALIZED TO IPHONE: PARTIAL (local descriptor dictionary proven; serializer/wire edge unproven)
SECOND DISPLAY APPEND POINT: unknown; no Honda display array proven here
```

This builder is not the same as the SETUP response's `streams` CFArray. One is a local display-info dictionary; the other is a list of negotiated stream response dictionaries. Do not equate them.

Sources: `primary-display-session.md`, `jmcs-address-map.md`, and local ignored ELF `extracted/system-vendor/system/bin/jmcs`.
