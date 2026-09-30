# Step 42B — Type111 security and session access matrix

## Step 42C contract addendum

Honda Type110's recovered KDF, session input, listener and crypto object remain Honda-owned and must not be borrowed or reset by a Type111 model. Existing offline KDF tests use generated master bytes. Candidate Type111 work must use a separate stream ID, independent candidate key/IV, and independent CTR/parser instance. This is a design isolation rule, not a Honda Type111 derivation claim. Reuse of authenticated master material, Type111 ID source, and exact KDF remain unknown.

The repository must not contain real key material or proprietary encrypted payload fixtures. Synthetic known-answer tests may use generated values only and must not carry Honda session provenance.

The matrix distinguishes the current Type110 implementation from a hypothesized Honda Type111 extension.

| State/material | Honda source | Outside jmcs now? | Needed for Type111? | Assessment |
|---|---|---|---|---|
| Authenticated AirPlay/iAP2 receiver session | Existing session object is passed to Honda Setup; live receiver thread/topology is separately observed. | No supported session IPC found; mapped service APIs do not hand it off. | **Unknown** whether Type111 is same authenticated session. | MHI2 suggests same receiver session, but Honda Type111 path absent. |
| 16-byte receiver-session master material | Honda Type110 KDF call reads the recovered session field and uses 16 bytes. | No evidence of export through CarPlayApService, ExternalDisplay API, or other reviewed Binder. | **Unknown for Honda Type111**; likely needed if it reuses Honda's/MHI2's per-stream derivation. | Keep strictly in memory; do not copy/log. |
| `streamConnectionID` | Supplied in Type110 request, read as nonzero uint64 and used as KDF input. | A network proxy might observe it only if it can receive the Setup bytes; no such path is proven. | **Unknown for Honda Type111**; required by pinned MHI2 implementation. | ID is peer-supplied for Type110, not Honda-generated there. |
| Type111 key/IV | No Honda Type111 derivation call. | No. | **Unknown** whether same KDF/inputs apply; encrypted-body receiver would need a compatible decrypt state if its stream is protected. | Separate CTR context is an isolation requirement of a two-stream design, not proof of Honda wire compatibility. |
| `dataPort` | Honda Type110 creates listener on port 0 and returns assigned port. | Not through existing Android service APIs. External proxy could create a listener only if iPhone is directed to it. | A response port is needed by the MHI2/xcertplay-style receiver pattern; Honda Type111 requirement unknown. | Separate listener ownership and phone reachability must be designed. |
| Setup request/response | Native request parser and response CF dictionaries live in jmcs; caller serializes synchronously to HTTP/binary plist. | Could be visible to a transparent proxy only if traffic is routed through it and the transaction can be parsed; neither is established. | Yes for any solution extending the current receiver's negotiation. | This ownership favors jmcs as target control-plane location. |
| Accepted data socket | Honda Type110 listener/accept/thread owns the current screen socket and NetSocket wrapper. | No FD or socket handoff API found. | A new receiver must own its own Type111 accepted socket. | Do not route a Type111 socket through Honda's Type110 parser without evidence. |
| Pairing/MFi/transport authentication | Static and live evidence identifies iAP2/USB machinery, but current raw Identification/auth payload is unavailable. | No. | **Unknown** for same-session extension; an independent full receiver would need its own compliant authentication path. | Full replacement receiver is a separate and much larger architecture. |
| Session timing/generation/teardown | Honda owns its receiver session and Type110 lifecycle. | Only summary app status callbacks are exposed to Java services. | Yes for correct secondary lifetime, though exact Honda Type111 lifecycle semantics are unknown. | ClarityLink would need independent generation/rollback state. |

## Independent receiver answer

A truly independent replacement receiver could in principle own its own authentication and derive its own session keys, but current artifacts do not establish that it can coexist with Honda's USB/iAP2 ownership and preserve the stock center screen/audio. An independent *secondary* listener that receives a Type111 request belonging to jmcs's session would need the compatible session security context, and no external API provides it. Therefore **independent Type111 receiver feasibility is UNKNOWN**, not disproven; no current evidence makes it the lower-risk path.

## Security handling constraints

All existing offline KDF tests use synthetic values. No real key, IV, session master or decrypted screen body is stored. Any later implementation would need an in-memory-only provider, a separate CTR context per stream, strict teardown zeroization, and logs limited to state/size/status metadata. These are design constraints, not authorization to deploy.
