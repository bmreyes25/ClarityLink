# R6C CarPlay control-session owner

**Owner in preserved build: `jmcs` (`HONDA_STATIC_CONFIRMED`).** `AirPlayReceiverServerCreate`, `AirPlayReceiverSessionCreate`, `AirPlayReceiverSessionSetup`, `AirPlayReceiverSessionTearDown`, screen setup, request dispatch, response construction, and serialization are in the same executable. [R3A's Setup path](43t1-r3a-setup-path-seam-map.md) traces the direct request/response path, and [R3C's cross-ELF audit](43t1-r3c-extension-path-matrix.md) found no imported Setup or serializer call in another preserved ELF. `/info` and SETUP therefore enter the internal AirPlay receiver. GET/SET_PARAMETER and event ingress were not independently closed in R6C.

The desired `AuthenticatedCarPlayChannel` (`receive_request`, `send_response`, `session_id`, `security_context`, `close`) has **no evidenced factory export**. `libcarplay_proxy.so` exports authentication, audio, and screen callback trampolines, not structured CarPlay request/response transfer. `CarPlayApService` Binder exports UI/status controls, not a native authenticated channel.

Transport decision: `R6C_FACTORY_TRANSPORT_PARTIAL`. The stack and ownership are identified inside `jmcs`, but a transferable or callable control channel is not. This is a scoped static conclusion, not proof that no future interface can be developed.
