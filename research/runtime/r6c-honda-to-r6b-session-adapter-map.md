# R6C Honda to R6B adapter map

| R6B contract | Honda source / evidence | Availability, conversion and blocker |
|---|---|---|
| `AuthenticationProvider.initialize` | `jmcs` `os_auth_cp_init`, `mc_carplay_proxy_auth_register` | Internal startup only. External lifecycle/permission ABI `EVIDENCE_REQUIRED`. |
| `authenticate → SessionHandoff` | `uwh_ipod_cp_*`, `ios_iap2_set_authenticated` | Hardware-backed operations visible, but no opaque authenticated AirPlay session export. `EVIDENCE_REQUIRED`. |
| `session_ready`, `session_identifier` | iAP2 auth state and AirPlay session object | Correlation/identity across them untraced. `EVIDENCE_REQUIRED`. |
| `transport_handle`, `CarPlaySessionTransport.read_request/write_response` | `jmcs` AirPlay request handler and serializer | No external request/response channel. `EVIDENCE_REQUIRED`. |
| `security_context`, `ScreenSecurityProvider` | AirPlay receiver-session master context and Type110 derivation | Session-private and no transferable security provider. Type111 relationship unproven. `EVIDENCE_REQUIRED`. |
| `ReceiverSession` generation/close | `jmcs` receiver creation/teardown | Internal lifetime; generation mapping needs explicit ownership contract. |
| `AudioRouter` | `jmcs` `mc_carplay_audio_*`, Android media | Separate API and audio continuity not proven. |
| `ControlRouter` | `jmcs` `handle_carplay_*`, iAP HID | Event direction/ownership partly visible; external delivery not proven. |

All target adapters in `honda_substrate.py` return `EVIDENCE_REQUIRED`; no Honda ABI is guessed. An opaque context token models generation and invalidation without serializing handle contents. The future binding must define ownership, threading, permissions, and close semantics before it can be used by R6B.
