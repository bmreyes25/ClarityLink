# R6F local authority inventory

Inventory date: 2026-10-05 (Mac host). Read-only `system_profiler SPUSBDataType`, `system_profiler SPBluetoothDataType`, and `ioreg -p IOUSB -l -w0` checks were used. Bluetooth output was reviewed locally and personal device identifiers were discarded; no Bluetooth peer is treated as CarPlay authority.

| Name | Vendor | Model | USB VID/PID | Connected? | Mac-visible? | MFi authority? | CarPlay receiver? | iAP2 owner? | Control-session owner? | Documented host interface? | Usable now? | Evidence |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Mac USB tree | Apple / attached USB devices | N/A | none enumerated | No candidate connected | Yes; empty of candidate devices | No candidate | No candidate | No candidate | No candidate | No | NOT_PRESENT | USB system_profiler and IOUSB registry showed no external USB devices; no serials retained |
| Mac Bluetooth controller | Apple | built-in controller | N/A | Controller on; no identified CarPlay accessory session | Yes | No | No | No | No | No | PRESENT_NOT_AUTHORITY | system_profiler Bluetooth inventory; personal peer identifiers intentionally omitted |
| LIVI Link / CPC200-CCPA | Carlinkit / LIVI | CPC200-CCPA, i.MX6UL family | Not present | No | No | Candidate only | Candidate radio/auth endpoint only | LIVI software would own | LIVI software would own | Public LIVI Link network interface, not connected | NOT_PRESENT | [LIVI Link docs](https://github.com/f-io/LIVI/blob/main/LIVI-LINK.md); no matching unit in local USB tree |
| OCBM-compatible CPC200-CCPA | Carlinkit / OCBM | CPC200-CCPA | Not present | No | No | Candidate genuine coprocessor per OCBM docs | Adapter owns session | Adapter | Adapter / OCBM stack | OCBM USB/NCM host protocol | NOT_PRESENT | [OCBM](https://github.com/lvalen91/ocbm); no matching unit in local USB tree |
| Licensed MFi service | Provider not selected | N/A | N/A | No configured endpoint | No | Unknown | Unknown | Unknown | Unknown | No documented endpoint configured | NOT_PRESENT | R6E configuration and provider discovery found none |

No authentication command was sent and no arbitrary device interface was opened. No receiver development CLI was found in PATH. No identity/configuration values or unrelated private files were inspected. Local result: no usable authority is present.
