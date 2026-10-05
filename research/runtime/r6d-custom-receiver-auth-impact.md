# R6D impact on the maintained custom receiver

**Decision:** no supported external Honda factory authenticated-session handoff was found. R6B's `HondaAuthenticationProvider`, `HondaIap2Transport` and `HondaCarPlaySessionTransport` must continue returning `EVIDENCE_REQUIRED`; creating another fake Honda adapter would hide the missing source. The custom receiver remains primary and stock `jmcs` interposition stays parked under R3C.

| Receiver contract | Consequence |
|---|---|
| `CarPlayTransport`, `AuthenticationProvider`, `CarPlaySessionTransport` | next engineering work must obtain an independently owned, lawful authenticated host transport and structured control channel; factory process-local pointers are not handoffs |
| `ReceiverSession`, `/info`, SETUP | continue R6B/R6A host implementation once a real authority/channel exists; no change to Type110 or Type111 transaction ownership |
| Type110/Type111 screen security | custom receiver must own negotiation and generation-scoped security; factory Type110 KDF is evidence, not an exported secret/context service; Type111 still requires real evidence |
| audio and controls | independent routing/adapter contracts remain open; proxy/Binder status callbacks do not guarantee stock-quality continuity |
| target deployment architecture | no target execution now; a future replacement process would need lawful USB/iAP2/auth ownership or a newly evidenced supported platform service, plus lifecycle, audio, controls and both displays |

Answers: **No** external reuse of authenticated Honda state is supported by the reviewed image. Authentication helper calls are **in process only**; whether a separately authorized replacement process could lawfully use the installed device with a supported API is `UNKNOWN`. **Yes**, Mac host development needs an independent lawful MFi authority and control-session owner. A final target that replaces `jmcs` may have to own the factory authentication path itself, but this is a future architecture hypothesis rather than an established API or permission to access hardware. The immediate R6E task is a host lawful-auth transport that produces a real R6B `SessionHandoff` and control requests.
