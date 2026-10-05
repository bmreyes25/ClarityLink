# R6A Type111 /info negotiation

`host_info()` now emits an AirPlay-shaped pair of `displays` entries with distinct UUIDs, type 110/111, dimensions, physical dimensions, FPS, features, input role, `viewAreas`, `initialViewArea`, and Type111 `initialURL`. These are structures rather than an `altScreen` Boolean fixture. It also emits prior-art `modes` resources. It is **not yet a complete receiver /info**: identity, HID, audio formats/latencies and authenticated session service are missing. No real iPhone request reached this Python receiver.

| Field / behavior | Provenance | Meaning / limit |
|---|---|---|
| two displays, Type111 request after advertised profile | CURRENT_IOS_LAB_CONFIRMED | [43P](../lab/current-ios-type111-observation.md), on PlayPort, not this receiver |
| Type111 before Type110, distinct IDs/ports | CURRENT_IOS_LAB_CONFIRMED | same 43P session |
| `viewAreas`, `initialViewArea`, `initialURL` present | CURRENT_IOS_LAB_CONFIRMED | profile-level presence only; causal requirement not isolated |
| display `uuid`, `type`, geometry, physical size, FPS, features, input role | EXTERNAL_PRIOR_ART | [PlayPort/xcertplay source](https://github.com/shilapi/xcertplay/blob/master/shared/src/main/java/com/shilapi/xcertplay/airplay/AirPlayInfoPlist.kt); values are synthetic host config |
| `modes` resources | EXTERNAL_PRIOR_ART | same implementation; field-level phone necessity unknown |
| 800×480 secondary geometry | INFERENCE | target logical output choice, not an iPhone-confirmed requirement |
| full audio/HID/identity /info | UNKNOWN | absent from this implementation; cannot claim complete profile |
| Type111 feature token negotiation | CURRENT_IOS_LAB_CONFIRMED | 43P PlayPort enabled `altScreen`/`viewAreas` in session Setup; Python host does not handle this transaction |

No field is labeled Honda Type111-confirmed. The real-lab gate requires completing identity, HID/audio and authenticated session handling before connecting a phone.
