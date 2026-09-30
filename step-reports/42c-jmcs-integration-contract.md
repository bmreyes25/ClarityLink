# Step 42C — offline jmcs Type111 integration contract

**Scope:** contract/design only, based on checked-in Honda static analysis, Steps 42A/42B, and current host models. No vehicle, ADB, firmware edit, binary execution, hook, preload, key, or live Type111 was used.

## Contract decision

The future target is a stock-first extension at the jmcs session/Setup boundary. Honda owns authentication, Setup, Type110 and audio. ClarityLink may prepare an isolated Type111 candidate only after stock Setup succeeds, then append a candidate response to a copy of the stock response. Any project failure rolls back only project-owned state and returns stock behavior. A separate ExternalDisplay-host adapter is the target frame sink, but no supported handoff exists. The digital twin remains the only active executable workstream.

## Type110 invariants

| Invariant | Honda confirmed | Preserve | Offline-testable |
|---|---:|---:|---:|
| Stock Setup request handling and supported audio/screen branches | Yes | Yes | Yes, model semantics |
| Type110 response type and Honda-selected dataPort | Yes | Yes, unchanged | Yes |
| streamConnectionID read and use in Type110 screen KDF | Yes | Yes | Yes with synthetic values |
| Recovered SHA-512 key/IV derivation uses session master and decimal ID salts; type is not a KDF input | Yes | Yes | Yes |
| Type110 listener/parser/CTR/decode path serves stock center CarPlay | Recovered static path | Yes | Partial; twin cannot execute Honda path |
| Honda audio and reconnect behavior | Existing stock ownership | Yes | Partial, synthetic lifecycle |
| Type111 failure cannot corrupt Type110 state | ClarityLink invariant, not Honda Type111 behavior | Yes | Yes |

The existing negotiation suite covers stock-first order, Type110/audio response preservation, unknown-field preservation, candidate rollback, and malformed merge atomicity. The display/session fixture checks primary preservation in data explicitly marked synthetic. No new test/code change was warranted for this documentation milestone.

## Input/output summary

Potential inputs include active authenticated session, original Setup request, stock status/response, stream list, optional /info descriptor source, Type111 identity/connection ID, session master input, derivation contract, listener factory, timing and teardown callbacks, error reporting, and renderer handoff. Honda makes the Setup request/stock response and Type110 KDF inputs available within the traced jmcs path; there is no reviewed outside-JMCS Binder transfer for security/session/socket or frame state. Exact Type111 ID, master reuse, KDF, callbacks and handoff remain unknown.

Outputs are candidate-only: optional display descriptor, Type111 response descriptor, separate listener/dataPort, separate security/parser/codec state, decoded frame lease, and bounded status. No Type111 response fields are promoted to Honda facts. The current MHI2-shaped response profile remains prior-art hypothesis.

## Type111 unknowns and lifecycle

The formal register covers response fields, advertisement requirements, display UUID correlation, ID source, port semantics, key/IV, master reuse, timing, Honda capability generation, parser changes, connection initiator, teardown/reconnect, and ScreenStream/H.264 reuse. Every row records impact, offline testability, live evidence requirement and next reduction step.

Candidate lifecycle: IDLE -> PREPARING -> LISTENING -> ADVERTISED -> CONNECTED -> STREAMING -> CLOSED. Port publication follows successful listener setup; response serialization failure closes the candidate listener. Type111-only failure clears only Type111 state. Parent-session teardown closes the child stream. The observed Type110 128-byte header and opcode interpretation are evidence for Type110 only; Type111 reuse stays a hypothesis.

## Security and renderer

Do not share Type110 CTR/parser state with Type111. Type110 uses a 16-byte session master and nonzero streamConnectionID in its recovered derivation; stream type is not part of that function. Type111 derivation/master reuse is unknown. All tests use generated values; no real keys or captured encrypted payloads belong in the repository.

Candidate renderer boundary is H.264/Annex-B -> decoder -> owned RGBA_8888 frame with dimensions, byte stride, timestamp, optional crop/rotation -> process-local ExternalDisplay host adapter. The current transport model stops at Annex-B access units and the renderer is a mock. Decoder ownership, IPC, crop/mask, safe area and host entry remain unknown. Center Display 0 is outside this adapter contract.

## Digital twin contract

Represent stock Type110, synthetic jmcs session lifecycle, a separate candidate Type111 generation, fake vehicle/display state, fake listener/renderer/ExternalDisplay host, errors and bounded synthetic timeline. Label fields as Honda-confirmed, MHI2-derived hypothesis, synthetic, or unknown. Unknown identity never defaults to Honda UUID; candidate failure is fail-closed and stock-only.

The twin can test internal state-machine, bounds, rollback, synthetic crypto isolation and renderer lifecycle. It cannot prove iPhone acceptance, Honda Type111 wire/security compatibility, linker entry, Binder handoff, physical Display 1 output, or live center preservation.

## Readiness gate

JMCS INTEGRATION CONTRACT: COMPLETE
TYPE110 INVARIANTS: DEFINED
TYPE111 INPUT REQUIREMENTS: PARTIAL
TYPE111 OUTPUT CONTRACT: PARTIAL
TYPE111 UNKNOWN REGISTER: COMPLETE
TYPE111 LISTENER LIFECYCLE: DEFINED
SECURITY CONTRACT: PARTIAL
RENDERER HANDOFF CONTRACT: PARTIAL
DIGITAL TWIN CONTRACT: DEFINED
MODEL UPDATES: NO
OFFLINE DIGITAL TWIN: READY
JMCS NO-OP TEST: NOT READY
EXTERNALDISPLAY RENDER TEST: NOT READY
TYPE111 LIVE WORK: NOT READY
LD_PRELOAD STATUS: PARKED
BIGGEST BLOCKER: no proven jmcs entry or ExternalDisplay frame handoff, while Honda Type111 response/security/correlation remain unknown

Complete means the boundary and preservation rules are defined. Type111-specific requirements remain partial because Honda does not implement/describe that path in the recovered stock receiver.

## Next

Extend the offline twin to exercise the written Type111 generation/listener-to-renderer contract with failure injection while preserving stock Type110. Keep hypothesis fields explicit and avoid deployment-seam work unless new evidence changes its parked status.
