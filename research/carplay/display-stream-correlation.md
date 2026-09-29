# Honda display-to-stream correlation — Step 29

The request and response traces now establish stream type dispatch but still do not join the display UUID to a stream. The `displays` property is a one-element array containing the main-screen dictionary. SETUP iterates a separate `streams` request array; type 110 selects the screen setup branch. That branch opens a dynamic listener and creates a response entry with `type=110` and `dataPort`.

| Candidate | Honda evidence | Status |
|---|---|---|
| Display UUID ↔ request type | UUID is local display property; request type 110 routes screen setup | No shared read/dataflow |
| UUID ↔ stream ID/connection ID | No Setup correlation recovered | Unknown |
| UUID ↔ dataPort | No shared object/dataflow | Unknown |
| Display-array index ↔ stream-array index | Independent arrays and loops | Unknown |
| Session object ↔ display/stream | Session enters Setup; direct display binding not shown | Unknown |

**DISPLAY-TO-STREAM BINDING:** type 110 selects the screen handler, but no identifier binds the advertised display object to that request or its response port. Confidence: high for the separation in analyzed code; actual protocol semantics remain unknown.
