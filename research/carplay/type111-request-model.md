# Type-111 SETUP request model — Step 34

This is an evidence classification, not a fixture or implementation. Honda source remains authoritative for Honda; the MHI2 descriptor behavior below is prior art only.

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

## MHI2 exact-request cloning

At pinned MHI2 commit `c2f811f1a5c84dae3a62f4cf9b4a9e65fc3f7b3c`, `libaltscreen111_gen2.c` reads the original request's `streams` array, selects the entry whose `type` is 111, clones that stream dictionary key/value-for-key/value, and changes only the response copy's `dataPort` and `streamID` before appending it to the stock response stream array. When stock needs to process other entries, `clone_without_111` clones the root request and replaces only `streams` with an array excluding type 111; all other root request fields and all fields of stock entries are retained. This is concrete prior-art source behavior, not proof that Honda accepts that shape.

The MHI2 source reads `streamConnectionID` from Type 111 and uses it to derive screen crypto with the stock session master material. No display UUID is used as transport crypto input in that path. See pinned source `src/native/altscreen111-gen2/libaltscreen111_gen2.c` and the `STREAM111_PROTOCOL.md` notes in MHI2.
