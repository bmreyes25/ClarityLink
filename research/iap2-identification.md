# iAP2 Identification and CarPlay display advertisement

**Verdict: raw packet not reconstructible from the saved offline artifacts.** Task B's success criterion is met with a bounded passive-capture plan. No wire capture was started and no packet fields or bytes were fabricated.

## What the static evidence separates

The copied `jmcs` ARM binary contains iAP2 identification state/function names, including `iap2_acc_id_start` (VA `0x20f390`), `iap2_acc_id_accepted` (`0x20f418`), `iap2_acc_id_update` (`0x17b334`), and strings `IAP2_IDENTIFICATION_START`, `IAP2_IDENTIFICATION_INFORMATION`, `IAP2_IDENTIFICATION_ACCEPTED`, `IAP2_IDENTIFICATION_REJECTED`, `IAP2_IDENTIFICATION_CANCEL`, and `IAP2_IDENTIFICATION_UPDATE_INFORMATION`. They confirm that an iAP2 identification state machine is present; they do **not** reveal its numeric message/parameter IDs, serialized field order, exact bytes, or values actually exchanged on the wire.

The binary also contains accessory-info/XML routines such as `j_iap2_get_accessory_info_values_from_xml` (VA `0x173894`), `set_accessory_info_values` (`0x15d4f0`), `form_acc_info_string_packet` (`0x1df0a8`), and `return_accessory_info` (`0x1e0398`). Targeted disassembly confirms the setter reads configured strings and integers. The inspected source path does not establish that these functions are the CarPlay screen-capability serializer or provide a complete call/serialization chain for the iAP2 Identification-information packet.

CarPlay screen information is a separate code path: `mc_carplay_app_init` creates and registers `gMainScreen`; `screen_add_props` reads CarPlay `ScreenProperties`; `AirPlayReceiverSessionScreen_CopyDisplaysInfo` (VA `0x287ae1`) obtains `ScreenCopyMain` (call at `0x287b0c`). The static path selects the main screen. Therefore the 800×480/max-30-FPS/touch settings are confirmed local receiver configuration, but they do not prove that the iAP2 Identification payload contains display dimensions, safe-area fields, a second display, or any particular serialized values.

## Field-level reconstruction status

| Field | Offline evidence | Wire status |
|---|---|---|
| iAP2 message-state names | Present as strings and state symbols in `jmcs`. | Names only; numeric IDs/lengths/sequence/ACK values unknown. |
| Display/session role | One configured main screen and a ScreenCopyMain advertisement path. | No live descriptor bytes; no second cluster descriptor proven. |
| Video width/height | `j_config.xml` primary screen values 800×480. | Configured values, not proven serialized iAP2 TLVs. |
| Maximum FPS | `MAX_FPS=30` in `j_config.xml`. | Configured value, not proven on wire. |
| Touch mode | `hifi` under `TOUCH_MODE=1`. | Configured input mode, not proven iAP2 parameter/byte. |
| Display UUID | A `displayUUID` property is used in receiver code; `ScreenCreate` can parse UUID values from a screen-property dictionary. The Honda initialization calls it without a supplied property dictionary. A nearby `CarPlayScreen1234` string was not proven to be the UUID. | Exact UUID and generation/default rule unknown. Do not use `CarPlayScreen1234` as an identified UUID. |
| Safe/view-area fields | No coordinates configured in the inspected `j_config.xml` or found in the focused receiver strings. | Unknown/possibly carried in a later screen-session response; not attributable to iAP2 Identification. |
| Accessory identity | `j_config.xml` configures Honda/HMCTBA and revision strings; static accessory-info routines read configuration. | Exact set, ordering, encoding, and inclusion in the live identification packet not established. |
| Lengths, TLV IDs, byte order, checksum/framing | Not exposed by the bounded reconstruction. | Unknown. No hex packet can be emitted without invention. |

## Minimum read-only capture plan

**No live capture is authorized or performed in this Step 5.** When separately scheduled, a single parked reconnection session can collect the needed evidence without modifying the head unit:

1. Put a capture-only USB 2.0 protocol analyzer inline between the iPhone and the Clarity's CarPlay USB host port. Record to the Mac, not to car storage. Begin recording before attaching/reconnecting the iPhone; passively record USB descriptor enumeration and both directions of control/bulk/interrupt traffic through the iAP2 Identification Accepted state. Do not use a programmable proxy that changes traffic.
2. Preserve raw transfers, direction, timestamps, bus/device address, endpoint number, setup packets, and payload bytes in a local `.pcapng`. Capture the exchange containing Identification Start/Information/Accepted; stop after initial CarPlay screen/session setup has been observed. The endpoint addresses are **not known offline**; the analyzer's passive enumeration supplies them. Do not assume an endpoint number.
3. In the same session, determine whether the screen-info response associated with `AirPlayReceiverSessionScreen_CopyDisplaysInfo` traverses the captured USB link. If not, first obtain a bounded read-only runtime socket/interface inventory for `jmcs`, then use a passive capture on only the observed iPhone↔receiver control endpoint/interface. The exact socket, port, interface, and transport for that display-session response are **not identified offline**, so no guessed filter or command is supplied.
4. Keep the PCAP and device identifiers local. Decode the Identification packet framing and field order from the captured bytes; separately locate the screen descriptor response. Record whether those later screen/session bytes are encrypted. Do not infer an unobserved field from the local config or a third-party implementation.

The available offline evidence records `CONFIG_USB_MON` as unset, so on-head-unit usbmon is not a supported capture route on this kernel. `jmcs` is the observed receiver/media-core process containing the iAP2 state machine and the CarPlay display-info path. The USB endpoint and any later socket remain runtime facts to collect. A Mac-side ADB session alone cannot recover payload bytes that were never captured.

## Exact packet decision

No deterministic packet-emitter script is appropriate: message/parameter IDs, parameter order, lengths, UUID, and framing/checksum are not established. The future capture must distinguish the raw iAP2 accessory Identification exchange from the later CarPlay/AirPlay display-session advertisement; the latter is the path relevant to screen count and view geometry.

## ClarityLink scope update — 2026-09-28

The practical target is a second independent CarPlay display routed into the cluster map region while the center display remains independent. Exact wire reconstruction remains open, but hardware purchase is not the next step: first use parked, read-only ADB to check existing USB-monitor support, available diagnostic tools, and targeted CarPlay/iAP2 logs. The latest `adb devices -l` check returned no device, so no live logs or vehicle-side checks were collected. The live descriptor transport remains unknown.
