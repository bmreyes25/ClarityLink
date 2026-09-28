# Static CarPlay screen/display-identification model

**Evidence class:** copied configuration plus focused ARM binary inspection. This is a static reconstruction of the receiver's configured primary-screen model. It is not a decoded iAP2 packet and not proof of every value actually serialized on a live session.

## Reconstructed model

| Property | Current static value/evidence | Confidence and limitation |
|---|---|---|
| CarPlay screen count | One Honda screen object is explicitly created as `gMainScreen` in `mc_carplay_app_init` (ARM virtual address `0xaff09`); it is configured and registered once in the inspected car-specific initialization. | High for this initialization path. Generic registry code can hold an array, but this Honda path shows one object. |
| Screen/session role | Main screen (`gMainScreen` / `ScreenCopyMain`). `AirPlayReceiverSessionScreen_CopyDisplaysInfo` at VA `0x287ae1` calls `ScreenCopyMain` at `0x287b0c`; that helper selects element zero. | Medium-high: current static advertisement is built from the main screen. It does not itself prove packet contents or that all live paths take this routine. |
| Logical video dimensions | 800×480 pixels. `j_config.xml` has `SDKCarPlay/ScreenProperties` `VIDEO_WIDTH_PIXELS=800`, `VIDEO_HEIGHT_PIXELS=480` at lines 165–167; `System/Display` separately lists 800×480 at lines 97–100. | High as configured dimensions; they apply to the configured primary display. |
| Maximum frame rate | 30 FPS (`MAX_FPS=30`, `j_config.xml:168`). | High as configured maximum; actual negotiated rate is not captured. |
| Touch capability | `TOUCH_MODE=1`, item `hifi` (`j_config.xml:170–172`). | High as configured screen input mode; serialized capability encoding is not established here. |
| Physical-size properties | `System/Display` lists 153×92 mm (`j_config.xml:97–100`). The native strings include `widthPhysical` and `heightPhysical` fields passed through `screen_add_props`. | Medium: configured dimensions and code keys exist; exact mapping to protocol units/fields is unverified. |
| Accessory identity configuration | The same `ServerProperties` block gives manufacturer `Honda`, model `HMCTBA`, firmware revision `1.F181.65`, and hardware revision `11.001` (`j_config.xml:155–163`). | High as local config strings; this field is not the Android build number and wire serialization was not captured. |
| Display UUID | Native strings/code keys include `displayUUID`; `AirPlayReceiverSessionScreen_CopyDisplayUUID` exists. No reliable UUID value or generation rule was recovered in this bounded inspection. | Unknown value. Do not invent one or copy a third-party receiver's UUID. |
| View area / safe area | No corresponding configured coordinates were found in the inspected `j_config.xml`; focused `jmcs` strings show legacy display keys but no `viewAreas`, `safeArea`, or `initialViewArea` strings. | Not found in this bounded search; strings absence cannot rule out numeric/obfuscated encoding. |
| Separate cluster display | No second car-specific screen creation/registration was found in `mc_carplay_app_init`. The proxy `mc_carplay_proxy_screen_register` at VA `0x1b7d` stores one callback structure and rejects another registration once its global flag is set. | High for the observed initialization/proxy constraints; no live negotiation trace. |
| iAP2 Identification bytes and component list | Not present in saved captures. No serialized accessory Identification packet, packet transcript, or decoded capability list is available. | Unknown. The static screen model must not be represented as reconstructed iAP2 packet bytes. |

## Why screen advertisement and iAP2 Identification are separated here

The inspected receiver code names `AirPlayReceiverSessionScreen_CopyDisplaysInfo` and supplies CarPlay display properties. That is a display/session information path. The iAP2 accessory Identification message and its component list are a distinct wire-level artifact. The available live logs, screenshots, manifests, and read-only Android state do not include that payload. This file therefore records the configured screen object and fields that can be traced statically, while marking all actual packet layout, encoded identifiers and values as unknown.

## Focused evidence sources

- `extracted/system-vendor/system/vendor/media/mcs/j_config.xml` — primary display and CarPlay screen configuration. SHA-256: `358cab78f4366d091cc4afa36d386ae8d9c21a81127091e2a2313ee6753240cc`.
- `extracted/system-vendor/system/bin/jmcs` — 32-bit ARM receiver binary. SHA-256: `cbc7ba881648fb8ffdfcc4c1100a028345c37134a2ae3b9dff7d76572851c232`. Focused disassembly results and function VAs are recorded in `research/native/receiver-multidisplay-audit.md`; this task did not decompile unrelated components.
- `extracted/system-vendor/system/lib/libcarplay_proxy.so` — screen callback boundary. SHA-256: `dc8bc5c19cf32a8e7edcc14c1d80e78bb96ca6ccc434229349c74590136bef66`.
- `research/NATIVE_CARPLAY_CLUSTER.md` and `research/native/receiver-multidisplay-audit.md` — prior static audit and confidence notes.

## Bounded conclusion

The evidence supports a statically configured single primary CarPlay screen at 800×480, up to 30 FPS, with a high-fidelity touch mode. The advertisement path selects a main screen; Honda's CarPlay proxy has a singleton screen callback. It does **not** identify live iAP2 Identification bytes, the UUID, view/safe areas, a second cluster display, or the exact primary Android Surface binding. Those remain separate protocol and rendering questions.
