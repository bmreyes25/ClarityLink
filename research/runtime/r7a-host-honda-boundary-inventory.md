# R7A host-to-Honda adapter boundary inventory

Date: 2026-10-06. This inventory describes host code and evidence only. It is not an Android or Honda implementation plan authorization.

| Boundary | R7A classification | Current contract / evidence | Remaining work |
|---|---|---|---|
| Authentication authority | `INTERFACE_COMPLETE` | `AuthenticationAuthority` and `SyntheticLabAuthenticationAuthority`; synthetic sessions are `MODEL_ONLY`. R6H LIVI/provider contracts remain separate. | A lawful genuine MFi authority and real authenticated session handoff are `EVIDENCE_REQUIRED`. |
| USB/iAP2 transport | `EVIDENCE_REQUIRED` | Historical Honda substrate is documented in R6C; no R7A USB/iAP2 transport implementation. | Establish protocol/session ownership and a permitted Android transport adapter in R7C. |
| Control-session transport | `IMPLEMENTED_HOST_TESTED` | Existing R6H same-UID Unix socket/provider path and synthetic `/info`+SETUP ownership; this milestone invokes the existing in-process negotiation contract. | Real iPhone control session and Android control transport remain `EVIDENCE_REQUIRED`. |
| Media transport | `IMPLEMENTED_HOST_TESTED` | Generation-owned IPv4 loopback listeners for Type110/111, bounded framing, independent socket state and disconnect cleanup. | Real Type110/111 listener bind/address/ownership and wire framing remain `EVIDENCE_REQUIRED`. |
| Type110 media security | `BLOCKED` | Generated clear-media fixture provider only; default non-lab path fails closed. | Real protocol and key handoff evidence required; no production crypto added. |
| Type111 media security | `BLOCKED` | Per-stream provider interface; generated-key host AEAD prior-art profile exists in earlier code; default is fail-closed. | Honda derivation and real Type111 key/nonce/header semantics remain unknown. |
| Software H.264 decode | `IMPLEMENTED_HOST_TESTED` | FFmpeg CLI decodes actual Annex-B access units and returns validated PNG dimensions. | Android decoder choice/format portability belongs to R7B. Honda hardware decoder support is unverified. |
| Audio output | `EVIDENCE_REQUIRED` | `/info` carries explicit synthetic capability fields only. No audio playback path in this receiver. | Define/implement an `AudioOutput` adapter and verify normal CarPlay audio in later work. |
| Input/steering controls | `EVIDENCE_REQUIRED` | HID capability fields are synthetic; no control event transport is implemented. | Define/implement an input adapter and verify controls/Siri without Honda-specific claims. |
| Primary display | `IMPLEMENTED_HOST_TESTED` | Independent host sink for Type110 frames with generation-tagged clear on teardown. | Android Display0 binding is an R7C target-specific task. |
| Secondary display | `IMPLEMENTED_HOST_TESTED` | Independent host sink for Type111 frames; 800×480 is a configurable host test size, not a Honda cluster safe area. | Honda Display1 admission, safe area, warning z-order and safety coexistence remain unknown. |
| Process lifecycle | `INTERFACE_COMPLETE` | One generation-scoped controller; synchronized transitions, per-stream teardown, rollback, reconnect and 100-cycle host test. | Honda process/service lifecycle and stock restoration remain `EVIDENCE_REQUIRED`. |
| Android API17/ARMv7 build | `ANDROID_API_DOCUMENTED` | Existing generic API17 research only; no R7A target compilation. | R7B must add reproducible API17/ARMv7 native build, toolchain pinning and target-compatible decoder/media interfaces. |
| Honda static evidence | `HONDA_STATIC_EVIDENCE` | Preserve R3C/R6 static findings and distinctions; R7A does not alter them. | New versioned artifacts would need their own bounded evidence review. |
| Honda executable compatibility | `UNKNOWN` | No Android/Honda executable or ABI run. | Validate only in later explicitly scoped milestones. |

`IMPLEMENTED_HOST_TESTED` means exercised in local synthetic tests, not that a Honda adapter exists. `INTERFACE_COMPLETE` does not mean an authority or target implementation is connected. Unavailable target adapters are not represented as implemented.
