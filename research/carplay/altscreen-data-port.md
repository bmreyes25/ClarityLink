# AltScreen data-port architecture

xcertplay `AirPlaySession.handleStreams` iterates requested stream dictionaries, calls `media.onScreen(session, type, stream)` for 110 and 111, and returns each accepted stream as `{type, dataPort}`. The media engine defines both screen type constants and owns its screen listener implementation. This proves a receiver implementation can provide per-stream ports in SETUP response; it does not prove all systems use a distinct listener or port per stream.

The Harman Type-111 native implementation contains an independent AltScreen receiver/thread and port configuration. This is reverse-engineered target-specific code. The reviewed source indicates the extension is integrated into the existing authenticated AirPlay receiver session and delegates session negotiation to stock code before extending the result. It does not show a new MFi identity or second iAP2 authentication ceremony for Type 111. Honda's transport keys, encryption context reuse, and listener handshake remain unknown.

| Question | Finding |
|---|---|
| Separate listener? | Yes in xcertplay per-screen engine path and Harman AltScreen receiver; independent implementation evidence |
| Listener before/during SETUP? | Must be available before the response advertises its port; exact startup ordering differs and Honda is unknown |
| Who selects port? | Receiver listener binds/configures; response returns selected port |
| Port in SETUP response? | Yes, xcertplay returns `dataPort` per accepted screen stream |
| Reuses existing session/security? | Likely in Harman interposer architecture; Honda specifics unverified |
| New authentication? | No evidence of separate MFi authentication in these implementations; do not claim confirmed for Honda |

Honda already has a primary ephemeral TCP listener (`bind(0)`, `getsockname`, then `CFDictionarySetInt64`) and accepts a stream socket, but the dictionary key and SETUP relationship are unresolved. That is only a likely architectural analogue, not proof its serializer can return a second port.
