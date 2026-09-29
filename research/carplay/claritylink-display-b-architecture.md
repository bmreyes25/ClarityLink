# ClarityLink Display B architecture — Step 29

## Evidence state

`CopyDisplaysInfo` builds a main-screen dictionary. `AirPlayReceiverSessionPlatformCopyProperty` handles the `displays` property by putting that dictionary into a one-item array. `AirPlayCopyServerInfo` invokes the property-copy routine, but the precise displays argument and any phone-facing serializer/send edge remain unproven.

SETUP parses the request body as a property list, reads a `streams` array, and dispatches each integer `type`: 100/101 audio and 110 screen. Type 111 follows the invalid-type path. Type 110 opens a dynamic listener and produces the response stream entry containing type and `dataPort`. No UUID, stream ID, or connection ID binds this response to the advertised display dictionary.

| Hook candidate | Evidence and status |
|---|---|
| Capability advertisement | No confirmed phone-facing boundary |
| SETUP request dispatch | `AirPlayReceiverSessionSetup`, type comparisons at `0x28590e` onward; Type 111 invalid path |
| SETUP response mutation | `_connectionHandleMessage` post-Setup/pre-serializer window remains structural; cannot by itself enable rejected Type 111 |

**Ready for negotiation implementation:** NO. **Ready for live experiment:** NO. Next work must identify the exact `displays` argument in `AirPlayCopyServerInfo` and trace its output to wire serialization, then determine a safe offline design for the explicit type rejection and correlation gap.
