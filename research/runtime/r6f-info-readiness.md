# R6F /info readiness audit

Source audit: `identity.py`, `info.py`, `capabilities.py`, and `receiver.py`. This file classifies what code supplies versus what is evidenced; `HOST_IMPLEMENTED` does not mean iPhone validated. No placeholder-backed `InfoProfile` is accepted by real preflight without per-family evidence.

| Field path | Type | Value source | Evidence level | Required? | Confidence | Real-iPhone risk |
|---|---|---|---|---|---|---|
| `deviceID`, `bluetoothIDs[]` | string | private lab identity file | HOST_IMPLEMENTED | Yes | Medium | Identity/transport binding not validated; never log raw ID |
| `name`, `model`, `manufacturer`, `sourceVersion` | string | profile JSON | UNKNOWN until sourced | Yes | Low | Random/common labels can be rejected or misidentify device |
| `features` | uint64 | profile JSON | UNKNOWN until lawful stack evidence | Yes | Low | Feature bitmap mismatch |
| `statusFlags` | integer | `capabilities.host_info` constant | HOST_IMPLEMENTED | Yes | Low | Meaning/value not iPhone-confirmed |
| `modes.resources[]` | array of resource maps | `capabilities.host_info` constants | HOST_IMPLEMENTED | Yes | Low | Resource semantics not validated |
| `displays[]` type 110/111 | arrays/maps | capability/profile geometry | HOST_IMPLEMENTED | Yes | Medium | Geometry, feature flags, view area semantics unsupported by real capture |
| display UUIDs | UUID strings | stable identity file | HOST_IMPLEMENTED | Yes | Medium | Must remain stable for identity lifetime; not Apple assigned |
| display width/height/maxFPS/physical size | integers | capability profile (defaults include 800x480/30) | INFERRED | Yes | Low | Defaults are placeholders until chosen Mac display evidence |
| `viewAreas[]`, `safeArea`, origins | maps/integers/boolean | capability builder | EXTERNAL_PRIOR_ART | Yes | Medium | Shape may differ from current iOS |
| Type111 `initialURL` | string | default map route | EXTERNAL_PRIOR_ART | Conditional | Medium | URL may be accepted only for specific media/session type |
| `audioFormats[]` | array of maps | explicit profile | UNKNOWN until captured from actual output stack | Yes | Low | Empty rejected; plausible but wrong values cause failure |
| `audioLatencies[]` | array of maps | explicit profile | UNKNOWN until measured/documented | Yes | Low | Unsupported units/ranges |
| `hidDevices[]` | array of maps, descriptor bytes | explicit profile | UNKNOWN until actual HID output evidence | Yes | Low | Synthetic descriptor likely rejected |
| `rightHandDrive`, keep-alive booleans | boolean | constants in `info.py` | INFERRED | Conditional | Low | Flags not validated against receiver |
| `/info` plist wire encoding and size guard | binary plist | `plistlib`/validator | HOST_IMPLEMENTED | Yes | High for serialization, none for compatibility | Wire acceptance remains unknown |

Evidence labels used: `CURRENT_IOS_LAB_CONFIRMED`, `PUBLIC_DOCUMENTED`, `EXTERNAL_PRIOR_ART`, `HOST_IMPLEMENTED`, `INFERRED`, `UNKNOWN`. **Real-mode gating:** the field profile must cite evidence for identity, receiver identity, display, screen modes, audio, HID, features, protocol versions, timing and secondary display; unknown required fields remain a blocker. `info-only` reports field paths/types and display types, not identity values.
