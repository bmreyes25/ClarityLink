# Honda `CopyDisplaysInfo` recovery (Step 28)

**Scope:** offline static review of the local `jmcs` ELF, its generated disassembly/string map, and tracked Step 26–27 evidence. No vehicle, ADB, ptrace, firmware patch, live hook, or protocol experiment.

## Function and output

`AirPlayReceiverSessionScreen_CopyDisplaysInfo` (Thumb VA `0x287ae1`, entry file offset `0x287ae0`) creates a mutable CF-style dictionary (`0x287af8`), calls `ScreenCopyMain` exactly once (`0x287b0c`), copies properties from that object, and stores the dictionary through its output pointer (`sl`, at `0x287cd0`). It releases the copied main-screen object and returns status. There is no loop, screen-array construction, or append in the function. `ScreenCopyMain` selects `gScreenArray[0]` and retains it.

## Recovered inserted fields

The values below are Honda-confirmed insertions. The keys are recovered from the string table at their literal addresses; property sources are `CFObjectCopyProperty` or `CFObjectGetPropertyInt64Sync` calls on the object returned by `ScreenCopyMain`. No runtime values were recovered.

| Key | Type/value | Source | Confidence |
|---|---|---|---|
| `edid` | object value, copied then `CFDictionarySetValue` | `CFObjectCopyProperty` | High: key literal and insertion call |
| `features` | numeric bitmask/value | `CFObjectGetPropertyInt64Sync`, transformed by bit masks, inserted with `CFDictionarySetInt64` | High insertion; exact semantic bits/value unknown |
| `maxFPS` | signed 64-bit-like CF number | property getter + `CFDictionarySetInt64` | High |
| `widthPhysical` | signed 64-bit-like CF number | property getter + `CFDictionarySetInt64` | High |
| `heightPhysical` | signed 64-bit-like CF number | property getter + `CFDictionarySetInt64` | High |
| `widthPixels` | signed 64-bit-like CF number | property getter + `CFDictionarySetInt64` | High |
| `heightPixels` | signed 64-bit-like CF number | property getter + `CFDictionarySetInt64` | High |
| `uuid` | signed 64-bit-like CF number in this recovered code path | property getter + `CFDictionarySetInt64` | High insertion/key; UUID representation is surprising and needs type/runtime confirmation |

The `uuid` insertion is numeric according to this call sequence; do not silently reinterpret it as a string UUID. No separate `screen type`, `role`, view area, input device, initial URL, primary/secondary designation, or display collection key is evidenced in this function. The opaque `features` bit meanings are unresolved. Physical dimension field names are literal keys, but runtime units are not established.

## Caller and container

A whole generated `jmcs` disassembly search found the function definition but no direct `BL` call site. Function-pointer/indirect use remains possible. The recovered output is a single dictionary, not an array. No tracked evidence places it inside an Identification, ReceiverInfo, feature plist, or larger capability dictionary. Exact callers, parent container, serializer, and send path therefore remain UNKNOWN.

```text
DISPLAY INFO PARENT: unknown; local output is one dictionary via out pointer
DISPLAY COLLECTION TYPE: no collection in this builder; singleton descriptor output
PHONE-FACING: unknown
DISPLAY ENUMERATION MODEL: singleton in this function; receiver-wide model unknown
```

The local feature/Identification notes distinguish this CarPlay display dictionary from raw iAP2 Identification. No wire bytes or Honda edge connecting the two are in the tracked evidence. See `honda-display-capabilities.md`, `honda-identification-receiver-info.md`, and Step 28.
