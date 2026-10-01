# Honda `CopyDisplaysInfo` recovery (Steps 28 and 43B)

**Scope:** offline static review of the local `jmcs` ELF, its generated disassembly/string map, and tracked Step 26–27 evidence. No vehicle, ADB, ptrace, firmware patch, live hook, or protocol experiment.

## Function and output

`AirPlayReceiverSessionScreen_CopyDisplaysInfo` (Thumb VA `0x287ae1`, entry file offset `0x287ae0`, size `0x248`) creates a mutable CF-style dictionary (`0x287af8`), calls `ScreenCopyMain` exactly once (`0x287b0c`), copies properties from that object, and stores the dictionary through its output pointer (`0x287cd0`). It releases the copied main-screen object and returns status. This function has no loop, screen-array construction, or descriptor append. In `ScreenCopyMain` (VA `0x2a17fd`), Honda locks `gScreenArray`, checks its count, fetches index zero, and retains that object. If no first entry is available, it creates/registers the main screen and returns it. DWARF names and source locations identify these routines in `ScreenUtils.c` and `AirPlayReceiverSessionScreen.c`.

Step 43B traced the backing property lifecycle: `screen_add_props` (`0xabd51`) writes the configured/global feature and display geometry values into the `gMainScreen` object; `ScreenCreate` can also consume a property dictionary and initializes the internal Screen object; `_ScreenCopyProperty` (`0x2a16ed`) maps property names to object fields. Thus the phone-facing descriptor is a projection of the single selected Screen object. This is not evidence of a general multi-display descriptor table.

## Recovered inserted fields

The values below are Honda-confirmed insertions. The keys are recovered from the string table at their literal addresses; property sources are `CFObjectCopyProperty` or `CFObjectGetPropertyInt64Sync` calls on the object returned by `ScreenCopyMain`. Values are not runtime captures. Property-source tracing is summarized in [ScreenCopyMain property sources](honda-screencopymain-property-sources.md).

| Key | Type/value | Source | Confidence |
|---|---|---|---|
| `edid` | copied object, then `CFDictionarySetValue` | Screen object property `edid` via `CFObjectCopyProperty` | High insertion; backing EDID source unknown |
| `features` | numeric bitmask/value, normalized by masks | Screen object property sourced from `g_screen_features`; inserted by `CFDictionarySetInt64` | High insertion/source family; exact bit semantics unknown |
| `maxFPS` | numeric CF value | Screen object property; configured global `g_screen_max_fps` is populated from `CarPlay/ScreenProperties/MAX_FPS` | High source chain to config key; runtime value unknown |
| `widthPhysical` | numeric CF value | Screen object property populated from `System/Display/WIDTH_MILLIMETER` into `g_screen_width` | High source chain to config key; unit implied by key, actual value unknown |
| `heightPhysical` | numeric CF value | Screen object property populated from `System/Display/HEIGHT_MILLIMETER` into `g_screen_height` | High source chain to config key; actual value unknown |
| `widthPixels` | numeric CF value | Screen object property populated from `CarPlay/ScreenProperties/VIDEO_WIDTH_PIXELS` into `g_video_width` | High source chain to config key; runtime value unknown |
| `heightPixels` | numeric CF value | Screen object property populated from `CarPlay/ScreenProperties/VIDEO_HEIGHT_PIXELS` into `g_video_height` | High source chain to config key; runtime value unknown |
| `uuid` | numeric CF value in this descriptor path | Screen object property; `ScreenCreate` declares a 16-byte local UUID buffer and has a generated/default property path, while caller-supplied properties may also seed the object | High insertion; whether the advertised number is stable or derived from that local UUID remains unproven |

The `uuid` insertion is numeric according to this call sequence; do not silently reinterpret it as a string UUID. `ScreenCreate` has a 16-byte local UUID buffer and generated/default construction logic, but the complete property source and stability policy are not proven. No separate `screen type`, `role`, view area, input device, initial URL, primary/secondary designation, or display collection key is evidenced in this function. The opaque `features` bit meanings are unresolved. Physical dimension field names and config keys are literal; no runtime values were recovered.

## Caller and container

The current caller/container path is established by the later, corrected Step 32 analysis: `AirPlayReceiverSessionPlatformCopyProperty("displays")` at `0x28d328` creates a mutable CFArray and appends this returned dictionary once; `AirPlayCopyServerInfo` inserts that array under `displays`; `_requestProcessInfo` passes the resulting object to the binary-plist `/info` response path. Older Step 28/31 wording below is retained as history and is superseded by this evidence.

```text
DISPLAY INFO PARENT: serverInfo["displays"] by Step 29/32 static dataflow
DISPLAY COLLECTION TYPE: mutable CFArray from the displays property handler; this function makes one dictionary
PHONE-FACING: CONFIRMED statically by Step 32
DISPLAY ENUMERATION MODEL: singleton descriptor emitted by this path; no alternate source established in the audited call path (binary-wide structural search remains inconclusive)
```

The mutable array makes a second entry mechanically representable at the collection level, but the recovered Honda code path selects one main Screen and appends it once. No second descriptor source was established. See [Step 43B](../../step-reports/43b-screencopymain-property-source-trace.md) and the [property-source trace](honda-screencopymain-property-sources.md).

The local feature/Identification notes distinguish this CarPlay display dictionary from raw iAP2 Identification. No wire bytes or Honda edge connecting the two are in the tracked evidence. See `honda-display-capabilities.md`, `honda-identification-receiver-info.md`, and Step 28.
