# R6B complete-shape /info field ledger

`InfoProfile` now requires identity, feature bits, audio formats/latencies, HID devices and R6A's dual-display profile. `build_info()` assembles a binary-plist-serializable dictionary and refuses missing audio/HID data. Its test profile is synthetic; no real iPhone accepted it. `load_or_create_identity()` creates stable local identifiers outside Git with owner-only file permissions. Their suitability for a particular Bluetooth/iAP2 handoff remains unproven.

| Field or family | Provenance | R6B status / limit |
|---|---|---|
| receiver name/model/manufacturer/sourceVersion | PUBLIC_RECEIVER_CONFIRMED | caller supplied, structurally emitted; live values require chosen auth stack |
| deviceID/bluetoothIDs | PUBLIC_RECEIVER_CONFIRMED | stable lab-only generated identity, never logged; physical Bluetooth identity correlation UNKNOWN |
| primary/secondary display UUID and type | CURRENT_IOS_LAB_CONFIRMED for two-display topology; EXTERNAL_PRIOR_ART for field shape | R6A emitter retained, distinct IDs |
| logical/physical dimensions, FPS, input role, features | EXTERNAL_PRIOR_ART | synthetic lab dimensions and caller feature bits; causal phone requirements UNKNOWN |
| safe/view areas and initial URL | CURRENT_IOS_LAB_CONFIRMED for presence in 43P profile | R6A emitter; exact geometry synthetic |
| rotation | UNKNOWN | not emitted; no evidence of requirement for the chosen profile |
| screen modes/resources | PUBLIC_RECEIVER_CONFIRMED | R6A host structure retained |
| audio formats/latencies | PUBLIC_RECEIVER_CONFIRMED as field families | required injected descriptors; real route and accepted values UNKNOWN |
| HID/input capabilities | PUBLIC_RECEIVER_CONFIRMED as field family | required injected descriptors; real reports/accepted values UNKNOWN |
| top-level features/statusFlags | PUBLIC_RECEIVER_CONFIRMED | feature bitset injected; no unverified default advertised |
| `altScreenURLs` | CURRENT_IOS_LAB_CONFIRMED | observed in the **iPhone's request**, not proven receiver `/info` response field; not fabricated in response |
| `enabledFeatures` | CURRENT_IOS_LAB_CONFIRMED | 43P session SETUP response field, **not** `/info`; future control adapter must negotiate it |
| timing/event/keepalive ports | PUBLIC_RECEIVER_CONFIRMED | session SETUP/transport-related response, not `/info`; unimplemented |

[Semantic diff tool](../../tools/r6b_info_diff.py) reports field/type/display/feature differences without values, secrets or raw identifiers. It needs a lawful sanitized known-good fixture before an actual phone compatibility claim. The R6B structure is complete in **shape** when the injected capabilities are supplied; the project has not demonstrated a complete current-iOS accepted `/info`.
