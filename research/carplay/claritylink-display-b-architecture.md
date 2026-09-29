# ClarityLink Display B architecture — Step 29

## Step 32 decision update

Hook A now has a proven static seam: `_requestProcessInfo` receives the mutable `AirPlayCopyServerInfo` object and passes it to the `/info` plist serializer. The Honda binary contains no literal or construction evidence for `FeatureKey`, `altScreen`, `viewAreas`, or `enabledFeatures`; modern prior art suggests Setup capability augmentation may be another logical change, but it does not establish Honda's requirement. Hook B must therefore be researched as capability handling plus type-111 support. Two-hook sufficiency and live readiness remain UNKNOWN/NO pending Setup schema, stream binding, and ABI evidence. See [Step 32](../../step-reports/32-airplay-info-phone-path.md).

## Step 31 decision update

`AirPlayCopyServerInfo` is global only in the regular symbol table and is not a dynamic export. No normal ELF consumer was found among the 45 mapped shared libraries; no runtime lookup key was found. The only recovered plist send chain remains tied to SETUP. Therefore Hook A has no identified phone-facing insertion point, and Hook B remains an unvalidated conceptual per-entry diversion. Two-hook sufficiency, display-stream binding, and readiness remain UNKNOWN/NO as detailed in [Step 31](../../step-reports/31-airplay-server-info-consumer.md).

## Step 30 decision

The local capability half is now better established: AirPlayCopyServerInfo queries displays, inserts the returned one-element CFMutableArray into its mutable result dictionary, and returns a CFLDictionaryRef. The missing edge is still decisive: no caller, serializer, or phone-facing send path for this server-info dictionary is proven. The separate SETUP response proof cannot fill this gap.

Type 111 is rejected at the Setup invalid-type branch beginning 0x2861f6. A per-entry dispatch intercept could conceptually preserve stock handling for 100/101/110, but live ABI and response/error behavior are not yet validated. Display UUID-to-stream binding remains unknown.

**Decision:** TWO_HOOK_ARCHITECTURE_SUFFICIENT = UNKNOWN; PRIMARY_PATH_PRESERVABLE = structurally plausible but unproven; OFFLINE_NEGOTIATION_IMPLEMENTATION_READY = NO; LIVE_NEGOTIATION_TEST_READY = NO. First recover the server-info consumer and phone-facing serializer boundary, then resolve Type-111 request/response correlation and ownership. See Step 30 report.

## Evidence state

`CopyDisplaysInfo` builds a main-screen dictionary. `AirPlayReceiverSessionPlatformCopyProperty` handles the `displays` property by putting that dictionary into a one-item array. `AirPlayCopyServerInfo` invokes the property-copy routine, but the precise displays argument and any phone-facing serializer/send edge remain unproven.

SETUP parses the request body as a property list, reads a `streams` array, and dispatches each integer `type`: 100/101 audio and 110 screen. Type 111 follows the invalid-type path. Type 110 opens a dynamic listener and produces the response stream entry containing type and `dataPort`. No UUID, stream ID, or connection ID binds this response to the advertised display dictionary.

| Hook candidate | Evidence and status |
|---|---|
| Capability advertisement | No confirmed phone-facing boundary |
| SETUP request dispatch | `AirPlayReceiverSessionSetup`, type comparisons at `0x28590e` onward; Type 111 invalid path |
| SETUP response mutation | `_connectionHandleMessage` post-Setup/pre-serializer window remains structural; cannot by itself enable rejected Type 111 |

**Ready for negotiation implementation:** NO. **Ready for live experiment:** NO. Next work must identify the exact `displays` argument in `AirPlayCopyServerInfo` and trace its output to wire serialization, then determine a safe offline design for the explicit type rejection and correlation gap.
