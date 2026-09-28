# Primary screen start request (evidence ledger)

**Verdict: request schema UNKNOWN.** The static trace reaches receiver-side stream creation, but does not identify a serialized request or a phone response. This ledger deliberately distinguishes local display configuration from request fields.

| Field/category | Source | Value | Serialized name/ID | Confidence |
|---|---|---|---|---|
| Screen object | `_ScreenThread` passes receiver screen-session object to `StartSession` | Existing session object | UNKNOWN | High for local pointer flow |
| Setup/context pointer | `_ScreenThread` passes pointer loaded at `[context + 0xb0]` | UNKNOWN | UNKNOWN | High for pointer flow; semantic type unknown |
| Display identity | `CopyDisplaysInfo` obtains `ScreenCopyMain` / registry index 0 | Main screen locally | UNKNOWN | High local; not proven request field |
| Display UUID | `displayUUID` copy/property API exists | UNKNOWN | UNKNOWN | Unknown |
| Session identifier | No decoded session value in bounded evidence | UNKNOWN | UNKNOWN | Unknown |
| Stream identifier | `ScreenStreamCreate` creates an object; no wire ID recovered | UNKNOWN | UNKNOWN | Unknown |
| Width / height | Local `j_config.xml` | 800×480 configured | UNKNOWN | High as config only; not proven serialized |
| Maximum FPS | Local `j_config.xml` | 30 configured | UNKNOWN | High as config only; not proven serialized |
| Touch | Local `j_config.xml` | `TOUCH_MODE=1`, `hifi` | UNKNOWN | High as config only; not proven serialized |
| Physical size | Local `System/Display` config | 153×92 mm | UNKNOWN | High as config only; not proven serialized |
| Codec/profile | H.264 handling exists | Negotiated value UNKNOWN | UNKNOWN | Partial handling evidence only |
| Latency/timing | Screen NTP/time synchronization helpers exist | UNKNOWN | UNKNOWN | API presence only |
| Device address/port | No association to this setup path recovered | UNKNOWN | UNKNOWN | Unknown |
| Role / UUID / application assignment | No corresponding request key/value recovered | UNKNOWN | UNKNOWN | Unknown |

The only established boundary is the call from `_ScreenThread` to the receiver-side `StartSession`, followed by local `ScreenStreamCreate` and `ScreenStreamStart`. No wire bytes are inferred from the configured values.
