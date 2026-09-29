# Honda display-to-stream correlation — Step 30

The confirmed Setup parser reads streams[] entries and integer type. Honda's Type-110 response entry contains type and a locally allocated dataPort. The recovered Setup flow does not establish a copied display UUID, streamID, streamConnectionID, or other per-stream correlation field. The local main-display descriptor contains a uuid key, but its insertion is numeric and no flow connects it to the Setup request or response.

| Candidate binding | Honda finding |
|---|---|
| Display UUID → requested stream | Unknown; no flow recovered |
| Stream type 110 → main screen setup | Confirmed by dispatch |
| Type 111 → alternate display | Rejected by this Honda dispatcher |
| streamConnectionID / streamID copy-through | Not found in analyzed Setup slice |
| Session/connection context | Session exists, but no display association established |

Pinned prior art: xcertplay uses separate main/alternate display descriptors and stream types 110/111; it conditionally enables altScreen. Harman's MHI2 implementation has native Type-111 handling. These implementations establish their own receiver-specific behavior only. Pinned evidence does not establish that display UUID alone triggers a Type-111 request or document a universally required mode/UI correlation message (modes, showUI, suggestUI, etc.).

**Conclusion:** DISPLAY_STREAM_BINDING = UNKNOWN. Honda evidence does not show that adding a second descriptor by itself is sufficient to cause or associate a secondary stream. Do not invent final descriptor values or Type-111 wire fields.
