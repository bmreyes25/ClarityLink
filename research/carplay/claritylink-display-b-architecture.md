# ClarityLink Display B architecture — Step 33

## Evidence-supported split

1. Honda's `/info` response contains `displays[]`; its current array has the one main-screen descriptor. The object is mutable between `AirPlayCopyServerInfo` return (`0x28a156`) and plist serialization (`0x28a19c`). This is a static mutation window, not a validated hook.
2. Honda SETUP handles type 110 and rejects 111. Type-110 reads `streamConnectionID` as uint64, uses it to derive and install per-screen AES key/IV, opens a per-stream ephemeral listener, and returns `{type: 110, dataPort}`.
3. The `/info` descriptor's numeric `uuid` property has no recovered link to `streamConnectionID`, screen setup, or stream type. No Honda binding structure containing both was found.

## Current architecture decision

An added Display B descriptor plus a future Type-111 handler are **not yet demonstrated sufficient** for a secondary TCP connection test. The open link is how the iPhone chooses a secondary-screen stream and how the Honda/ClarityLink side identifies that stream as Display B. A distinct connection ID may be needed for key derivation, based on the stock Type-110 pattern, but Type-111 parity is unknown.

| Question | Current answer |
|---|---|
| Server-info augmentor offline model | Ready as a boundary/schema model; exact Display-B values remain unproven |
| Type-111 offline request/response model | Not ready as a complete contract; only evidence-labeled sketches |
| Can a second descriptor alone induce Type 111? | Unknown |
| Does display UUID bind to stream ID? | No Honda evidence found |
| Must mode/UI control precede Type-111? | Unknown; prior-art separates media from UI ownership |
| Is Type-110 crypto behavior reusable for 111? | Unknown; do not assume |
| Partial stock Setup delegation | Structurally plausible, semantics unknown |
| Live negotiation test ready | No |

No hooks, code, or live test are part of this architecture note. Next offline work should recover the screen UUID's source/layout and complete the accepted-socket-to-screen-session binding, then inspect prior-art commits/history for a clearly versioned Type-111 schema and feature-token requirement. Honda evidence remains authoritative for Honda behavior.
