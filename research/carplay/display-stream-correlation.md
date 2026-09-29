# Display-to-stream correlation

No Honda evidence currently ties a display descriptor to a negotiated stream. `CopyDisplaysInfo` inserts a local `uuid` key from a numeric property, while Setup response stream entries carry `type=110` and `dataPort`; no cross-reference between those objects has been recovered. The meaning and representation of the `uuid` value need runtime/type confirmation. `streamConnectionID` exists in nearby protocol strings but has not been tied to the display descriptor or a Type-111 path.

| Candidate correlation | Honda evidence |
|---|---|
| Display UUID ↔ stream type | Unknown |
| Display UUID ↔ `streamConnectionID` | Unknown |
| Display UUID ↔ data port/listener | Unknown |
| Descriptor index ↔ stream array index | Unknown |
| Session ID ↔ display/stream | Unknown |

**DISPLAY-TO-STREAM CORRELATION:** unresolved. Before appending Type 111, recover the phone's request identity fields and the receiver's parser/binding behavior; otherwise the receiver cannot be shown to associate the stream with a particular advertised display.
