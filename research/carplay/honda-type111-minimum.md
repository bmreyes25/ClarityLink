# Honda Type111 minimum negotiation (hypothesis)

Existing Honda request parser reads `streams[]`; type 110 follows stock screen setup; type 111 is unhandled/invalid-type path. Honda Type110 response includes `type=110` and a dynamic `dataPort`, and is serialized to the phone. A future Type111 listener must be separately owned and cleaned up; stock Type110 behavior should remain unchanged.

| Proposed item | Evidence |
|---|---|
| `/info` display descriptor | HONDA CONFIRMED one-element array; second descriptor acceptance UNKNOWN |
| SETUP `streams[]` / `type=111` | HONDA CONFIRMED parser recognizes type field; Honda has no handler |
| Type111 `streamConnectionID` | PRIOR ART / Honda security contract partially indicates per-stream ID; exact accepted field path must be checked against Step 38 evidence |
| Response `type=111`, `dataPort` | PRIOR ART only; Honda schema UNKNOWN |
| correlation and required security fields | UNKNOWN |
| iPhone secondary TCP connect | UNKNOWN on Honda |

Minimum conceptual sequence: `/info` advertises a compatible secondary display; phone sends a second stream in Setup; stock Setup handles primary; extension handles only Type111; listener returns bounded port and owns security/session state. No guessed fields are implemented. Negotiation implementation is NOT READY.
