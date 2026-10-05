# R6B host session transport and ownership

The existing 43P PlayPort lab follows Bluetooth/iAP2 bootstrap → MFi authentication → Wi-Fi/AirPlay pairing → encrypted control session → `/info` → SETUP → screen sockets. [PlayPort source](https://github.com/youcci/playport) contains `WirelessBootstrap`, `MfiIdentity`, `AirPlaySession`, `CarPlayMediaEngine`, and `ScreenStream`. The installed checkout's default key-file path refers to a recovered shared identity and is excluded by R6B. Its alternative remote-auth provider requires a separately authorized licensed service; none is configured in ClarityLink. PlayPort currently owns and consumes its control session internally; no public handoff is implemented to ClarityLink.

| Transition | Current owner | Interface/data | ClarityLink boundary | Blocker |
|---|---|---|---|---|
| physical link → iAP2 | PlayPort Bluetooth bridge or future hardware adapter | iAP2 bytes and identification | no Python adapter | lawful supported bootstrap and host interface |
| iAP2 → MFi auth | PlayPort `MfiAuthenticator` or genuine coprocessor project | certificate/challenge/sign operation | `AuthenticationProvider` accepts only result, no keys | authorized hardware/service and integration |
| auth → CarPlay control | PlayPort `AirPlaySession` | paired/encrypted RTSP requests | `SessionHandoff` + `CarPlaySessionTransport` | no exposed authenticated channel |
| control → `/info` | PlayPort internal handler | structured request/response | `ReceiverSession` and `InfoProfile` | injected full capabilities, real handoff |
| `/info` → SETUP | PlayPort internal handler | binary plist stream arrays | R6A `Receiver.setup` via `ReceiverSession` | real request not reached |
| SETUP → media | PlayPort screen listener | Type110/111 sockets | R6A listeners and media profiles | reachable bind and session keys |

`LabSessionTransport` delegates decrypted structured requests to an injected authenticated channel. It checks generation, timeout, response ownership and shutdown. `ReplaySessionTransport` is bounded and advertises `authenticated=False`. Tests with a fake external channel prove the adapter contract only. No socket is opened on a non-loopback interface, and no live iPhone control request has reached ClarityLink.
