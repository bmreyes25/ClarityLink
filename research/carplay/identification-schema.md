# CarPlay display / session schema evidence

**Verdict: partial local schema; wire schema unresolved.** Do not interpret this table as iAP2 Identification TLVs. The screen properties flow through the `AirPlayReceiverSessionScreen_CopyDisplaysInfo` path; the iAP2 Identification packet is a separate unresolved artifact.

| Field | Type / size | Source | Primary value | Display B requirement/value | Confidence |
|---|---|---|---|---|---|
| Display role | Unknown enum/string; wire size unknown | `gMainScreen`, `ScreenCopyMain` | main | cluster/alternate role unknown | Main role high locally; wire enum unknown |
| Display UUID | UUID-like property; representation unknown | `displayUUID` code/property names | Value and default unknown | Must be unique if protocol binds streams by UUID; format/requirement unknown | Unknown |
| Pixel width / height | Integers in config; wire type/size unknown | `j_config.xml` `VIDEO_WIDTH_PIXELS`, `VIDEO_HEIGHT_PIXELS` | 800×480 configured | 800×480 is only the Android output canvas; iPhone-facing size unknown | Config high; wire unknown |
| Physical width / height | Integer config values; wire mapping unknown | `System/Display` width/height mm | 153×92 mm | Unknown / likely not needed for initial model absent protocol evidence | Config high; protocol mapping unknown |
| Maximum FPS | Integer config; wire type/size unknown | `MAX_FPS` | 30 configured maximum | Unknown | Config high; negotiated value unknown |
| Touch mode | Config enum/list; wire encoding unknown | `TOUCH_MODE=1`, child `hifi` | hifi | Unknown; cluster may be non-touch but no protocol evidence | Config high; B unknown |
| Input capability | Not recovered | touch/HID config adjacent, no descriptor binding proven | Touch-screen HID configured separately | Unknown | Unknown |
| Rotation/orientation | Not recovered | No field traced in bounded sources | Unknown | Unknown | Unknown |
| Display features / safe area | No schema recovered | Focused config and symbol evidence | Unknown | Unknown | Unknown |
| Codec/profile | H.264 code present; negotiation schema unknown | `jmcs` H.264/stream code | H.264 handling present; profile unknown | H.264 candidate only; profile/format unknown | Partial |
| Session ID | Type, width, source unknown | No observed setup response | Unknown | Requires independent identity if protocol uses session IDs; actual requirement unknown | Unknown |
| Stream ID | Type, width, source unknown | Generic stream callbacks only | Unknown | Must route separately if multiple video streams are accepted; exact field unknown | Unknown |
| Main/alternate flag | No wire field recovered | Main screen selection path | Main locally | Alternate role/flag unknown | Local main high; B unknown |
| Night/appearance | Honda config has `NIGHT_MODE_CONTROL=manual`; no screen schema link | `j_config.xml` | local setting only | Unknown | No protocol mapping |
| Navigation capability/app assignment | Not recovered | No Display B selection code found | Unknown | Unknown | Unknown |
| iAP2 component/parameter IDs | Numeric IDs, lengths, order unknown | iAP2 state names only | No bytes | Unknown | Unknown |
| Framing/checksum/byte order | Unknown | No raw packet | Unknown | Unknown | Unknown |

No binary serializer is provided because doing so would require inventing identifiers, UUID rules, field order, or framing. The offline candidate model at [`../../src/carplay-session-model/model.py`](../../src/carplay-session-model/model.py) emits only deterministic JSON with explicit unknown markers.
