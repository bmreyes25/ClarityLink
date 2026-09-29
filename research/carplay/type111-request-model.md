# Type-111 SETUP request model — Step 33

This is an evidence classification, not a fixture or implementation.

| Field/behavior | Classification | Evidence |
|---|---|---|
| `streams[]` element with integer `type` | Honda-confirmed structure | `AirPlayReceiverSessionSetup` parses an array of stream dictionaries and reads `type` as integer |
| `type = 111` | Prior-art convention; Honda rejects it | Honda invalid-type branch at `0x2861f6`; xcertplay/MHI2 describe Type 111 as auxiliary screen |
| `streamConnectionID` as uint64 | Proven for Honda Type 110; likely for Type 111, not proven | Type-110 inlined `_ScreenSetup` reads uint64 and passes it to screen key derivation |
| display UUID in request stream | Unknown | No use/copy found in analyzed Honda path |
| timing/security fields | Unknown for Type 111 | Honda Type-110 uses session master key plus stream ID for AES key/IV; Type-111 requirements cannot be inferred as identical |
| response identity echo requirement | Unknown | Honda Type-110 response builder observed emitting type and dataPort, with no ID echo found |
| control-plane mode/UI state | Unknown as a prerequisite for Type 111 | Prior-art has UI/mode handling; Honda ordering is not recovered |

Do not use a fabricated Type-111 request dictionary as a production contract. Minimum next evidence is receiver/version-specific request capture or a fully recovered compatible prior-art parser and its wire schema, followed by an offline parity model.
