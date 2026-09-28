# Display B second CarPlay session model

**Status: candidate model implemented; protocol negotiation is blocked by missing descriptor/setup evidence.** This report separates the confirmed Android output canvas from the unknown iPhone-facing Display B protocol values.

## Candidate Display B

Display B is modeled at 800×480 because that is the confirmed Android Display 1 canvas. This is a ClarityLink output contract, not evidence that the iPhone should be advertised 800×480. The CarPlay logical dimensions must come from supported protocol/receiver evidence. Display B UUID, role encoding, session ID, stream ID, codec profile, FPS, touch/input capability, and app assignment remain unknown.

The offline data model is in [`src/carplay-session-model/model.py`](../../src/carplay-session-model/model.py). It preserves Honda's known primary values, allows a candidate cluster display and session descriptor, checks dimension and explicit UUID consistency, and emits deterministic JSON research fixtures with explicit `unknown` values. It deliberately emits no protocol packet bytes.

## Independence boundary

| Relationship | Evidence status |
|---|---|
| Display descriptor to display UUID | Property/API names exist; actual UUID value/default and wire binding unknown |
| Display descriptor to session | No observed setup response or binding field |
| Session to video stream | Generic `ScreenStream` lifecycle callbacks and H.264 code exist; IDs/ownership and a second stream setup are unknown |
| Stream to application content | No Display B app-selection/assignment evidence |
| Display B independent from Display A | Not established by a second Android display or a synthetic model; requires a distinct accepted CarPlay display/session/stream and independent lifecycle |
| Center session preservation | Honda's current primary setup is known, but no extension has been tested |
| Decoder handoff | Expected metadata includes accepted stream/session identity, codec/profile, coded dimensions, timing, and independent start/stop; actual fields and callbacks from the phone are unknown |

The exact point where evidence stops is after local `ScreenCopyMain` display-info construction and before a decoded phone setup/response is available. `_ScreenThread` calls `AirPlayReceiverSessionScreen_StartSession`, which establishes a receiver-side session context, but the saved analysis does not reconstruct its incoming request/transport fields or its binding to a video stream. `mc_ScreenStreamInitialize` stores a stream context and increments `g_screen_streams_cnt`, but this generic counter does not establish that Honda advertises or dispatches a second CarPlay stream. The proxy's global callback table is a concrete single-registration limitation.

## Strategy comparison

| Strategy | Required changes / control point | Protocol risk | Center-display impact | Second session support | Reversibility |
|---|---|---|---|---|---|
| A. Extend Honda configuration | Add/alter config and likely native initialization to create another screen | High; current code selects only main screen and has no evidenced B schema | Low if ignored; unknown if unsupported config destabilizes initialization | Not by config alone; singleton proxy remains | Config is easy to revert but not an evidenced complete path |
| B. Interpose/extend Honda receiver | Add display/session handling at `jmcs` display-info/setup boundary and replace singleton proxy dispatch with per-stream routing | High; protocol schema and receiver ABI are missing | Medium-high; must preserve primary callback/audio/session path | Architecturally plausible, not proven feasible on this build | Medium-low until nonpersistent hook and rollback exist |
| C. Separate ClarityLink protocol component | Implement a peer/control/stream endpoint alongside Honda primary | Very high; transport ownership, authentication, and coexistence are unknown | Potentially high due competition for iAP2/USB ownership | Unknown; no evidence another component can join the current phone link | Isolatable in code, runtime ownership/reversibility unknown |

**Preferred next engineering direction: B as an offline receiver-extension design**, because it can plausibly reuse the authenticated primary transport while extending its display-info/session lifecycle. This is not deployment readiness. A second `ScreenRegister` or XML entry alone is insufficient.

## Offline model limits

The model's canonical UTF-8 JSON output is only a deterministic fixture for tests. It is not iAP2, AirPlay, or CarPlay serialization. Unknown values use an explicit object rather than invented bytes. Once field IDs, nesting, byte order, and message framing are evidenced, a separately named wire serializer can be added with captured fixtures.

## Future decoder handoff

| Input to decoder/renderer | Evidence status |
|---|---|
| Stream/session ID | Unknown; no accepted Display B setup response observed |
| Coded dimensions | Primary config is 800×480; B dimensions and coded-vs-output relationship unknown |
| Codec/profile | H.264 processing code exists; negotiated profile/level unknown |
| Frame rate / timestamps | Primary config caps at 30 FPS; B cadence/timebase unknown |
| Start/stop/reconnect | Generic `ScreenStream` callbacks exist; B lifecycle and callback-to-display association unknown |
| Decoder destination | No primary-to-Android Surface mapping fully recovered; B-to-Display 1 path not implemented |

At the eventual boundary, ClarityLink will need the accepted stream identity, codec parameters, coded dimensions, presentation timestamps/timebase, and explicit start/stop/error events. It must preserve independent primary and secondary teardown. These are interface requirements, not evidence that Honda or iOS currently supplies them.

## Missing evidence and readiness

**Raw Identification capture required: MAYBE.** The artifacts cannot recover exact iAP2 parameter IDs, values, ordering, lengths, or framing. A passive capture could settle those bytes, but the screen descriptor is built in a separate AirPlay receiver display-info callback; an iAP2-only capture may not expose it. The precise missing evidence is (1) serialized current-display info or a captured equivalent containing UUID/role/size/touch/FPS fields and (2) the phone's accepted second-display setup response binding an independent video stream/session to Display B. The receiver-side socket/transport for that latter exchange is not identified, so do not assume an iAP2/USB filter will reveal it.

**Ready to implement real Display-B negotiation: NO.** The candidate model is testable; protocol correctness is not. Next, continue from `_ScreenThread` → `AirPlayReceiverSessionScreen_StartSession` to recover the request/transport and trace screen-stream callback dispatch to the concrete decoder/output consumer. If those call edges are unavailable in the saved binary, define a passive, narrowly scoped observation of those exchanges before selecting equipment.
