# CL-R9A — `/info` and control-SETUP feature negotiation

**Scope:** source inspection and preserved static notes only. No Honda receiver modification, device access, ADB, firmware patch, or live phone test. `safeForHonda()` remains `false`.

## Decision

The evidence establishes **no known Honda secondary negotiation contract**. It does not establish a supported Honda feature-negotiation API. Honda's recovered internal path is observable in static analysis, but it is not a public extension contract. The inspected path serializes a one-entry main display array and processes Type110; the available notes do not recover an accepted feature set or Type111 response. This is a bounded finding about the reviewed `jmcs` artifact and paths, not proof that no unexamined mechanism exists.

Decisive missing interface: a Honda-authorized, versioned contract that gives a caller the phone-facing `/info` display advertisement and per-session control-SETUP proposal/response, including feature ownership, stream admission, transport readiness, and teardown/rollback. Alternatively, new authorized static artifacts must show a supported extension API and the complete dataflow; runtime proof would need separate authorization. Existing private static research remains local and is not reproduced here.

## Audi implementation inspected

Reference: `luka-dev/mib2q-carplay-rgi` at inspected upstream HEAD `71b4ab1c9461d5383a7aa6d56d4dda34f567ade7`, files [altscreen_hook.c](https://github.com/luka-dev/mib2q-carplay-rgi/blob/71b4ab1c9461d5383a7aa6d56d4dda34f567ade7/hook/altscreen/altscreen_hook.c), [airplay_seams.c](https://github.com/luka-dev/mib2q-carplay-rgi/blob/71b4ab1c9461d5383a7aa6d56d4dda34f567ade7/hook/framework/airplay_seams.c), [ALTSCREEN_CLUSTER_VIDEO.md](https://github.com/luka-dev/mib2q-carplay-rgi/blob/71b4ab1c9461d5383a7aa6d56d4dda34f567ade7/docs/altscreen-and-video/ALTSCREEN_CLUSTER_VIDEO.md), and [CARPLAY_FEATURE_SURVEY.md](https://github.com/luka-dev/mib2q-carplay-rgi/blob/71b4ab1c9461d5383a7aa6d56d4dda34f567ade7/docs/altscreen-and-video/CARPLAY_FEATURE_SURVEY.md). The inspected branch calls itself a verified iOS 26.6 activation path; it is not an Apple-published protocol specification.

Direct source behavior in `altscreen_hook.c`:

- `AirPlayCopyServerInfo` is interposed at the framework seam in `airplay_seams.c`; the returned mutable dictionary is then available before `/info` serialization. The hook conditionally publishes `extendedFeatures`, `displays`, and `displayPanels` together after preflight.
- Its display builder preserves the stock main descriptor/UUID, then synthesizes a second cluster descriptor. The secondary identity is distinct; the source populates separate `uid`/`uuid` values for different consumers. Main and cluster `initialVideoStreams`, geometry and `viewAreas` are explicitly constructed.
- `extendedFeatures` contains `altScreen` and `viewAreas`. This advertisement is separate from the later SETUP response.
- `AirPlayReceiverSessionSetup` is wrapped by `airplay_seams.c`; module callbacks run after stock processing. `alt_on_setup_response` identifies control SETUP by a request `features` key, retains any existing response `enabledFeatures`, adds only features that this hook says it implements, and rolls back its advertisement if the response feature list cannot be built.
- The source checks whether the request contains a Type111 stream and only then calls `alt_setup`. Its own comments say stock handles 100/101/110 and skips 111. `alt_setup` prepares the second transport and appends the Type111 response; an unsuccessful setup changes the result to an error rather than returning success without a usable data port.

Separate author-reported reverse-engineering (not independently verified here): the docs and code comments attribute to iOS 26.6 AirPlaySender/CarKit disassembly that the phone proposes under request `features`, reads negotiated values from response `enabledFeatures`, requires two displays plus enabled `altScreen`, and selects 110 versus 111 using a display UUID comparison. They report that `extendedFeatures` alone does not activate this gate. The code comments also report the observed order control SETUP before `/info` on that iOS version, which is why it caches a preflight display tree. These are target/version-specific findings, not universal iPhone behavior.

The docs' flow says Type111 is offered after the phone has accepted the feature negotiation and recognized multiple displays; the receiver only sets up its transport when Type111 is actually present in a subsequent stream SETUP. The feature survey likewise cautions that each capability needs advertisement and message confirmation, and that stock advertisement was not exhaustively checked. Nothing in the Audi source transfers to Honda by analogy.

## Honda evidence matrix

`STATIC_HONDA_EVIDENCE` means a static path in the preserved reviewed artifact is documented in the local analysis. It is not a verified public contract. `VERIFIED_HONDA_CONTRACT` is intentionally unused: no authorized Honda contract was found.

| Audi source / symbol | Observed Audi behavior | Honda source/evidence reference | Honda finding | Class | Missing proof | Compatibility consequence |
|---|---|---|---|---|---|---|
| `airplay_seams.c`: `AirPlayCopyServerInfo`; `altscreen_hook.c`: `build_displays`, `/info` mutation | Mutates stock `/info` output before serialization; publishes display arrays and extended feature list after preflight. | `research/carplay/honda-info-type111-differential.md`; Step 32 path and `AirPlayReceiverSessionScreen_CopyDisplaysInfo` | Phone-facing `displays` array is built through one `ScreenCopyMain()` descriptor and serialized. | `STATIC_HONDA_EVIDENCE` | Authorized extension point, second display producer, runtime iPhone response. | No supported Honda advertisement API follows from mutability of an internal response object. |
| `altscreen_hook.c`: main and cluster display builders | Preserves main UUID; adds separate cluster descriptor with distinct display identity; uses `displayPanels` too. | Same differential; `honda-screencopymain-property-sources.md` | Main descriptor has numeric `uuid`; source/stability semantics unknown. No second descriptor in recovered path. | `STATIC_HONDA_EVIDENCE` | Stable identity across sessions; Honda secondary descriptor and field semantics. | Do not synthesize/clone identity or assume Audi's UUID mapping. |
| `altscreen_hook.c`: `build_extfeatures`; `AirPlayCopyServerInfo` | Builds `extendedFeatures=[altScreen,viewAreas]` and publishes atomically with display metadata. | `honda-info-type111-differential.md`; exact-literal audit plus `/info` trace | No `extendedFeatures` construction in recovered builder; token literals absent in reviewed ELF scan. | `STATIC_HONDA_EVIDENCE` | Alternate encoding/generic key path and authorized capability contract. | Cannot claim Honda consumes these tokens or advertise them. |
| `airplay_seams.c`: `AirPlayReceiverSessionSetup`; `alt_on_setup_response` | Observes setup request and post-stock response in a module seam; gate checks request `features`. | `honda-setup-stream-identity.md`; `honda-stream-type-dispatch.md` | Honda Setup parses `streams[].type`; reviewed notes do not establish a feature proposal being read. Exact token absent. | `STATIC_HONDA_EVIDENCE` | Full request dictionary dataflow for feature arrays/alternate keys; extension permission. | Audi callback order and keys cannot be assumed in Honda. |
| `altscreen_hook.c`: response `enabledFeatures` merge | Preserves existing accepted values, adds implemented values only, and avoids echoing proposal. | `honda-setup-stream-identity.md`; `honda-response-serializer.md`; `honda-info-type111-differential.md` | Honda owns a mutable Setup response for stock stream entries and serializes it. No enabled feature set is recovered; exact key absent. | `STATIC_HONDA_EVIDENCE` | Whether the response contains another equivalent field, who owns negotiated capabilities, whether mutation is supported. | No proven Honda negotiation response; never infer accepted values from request. |
| `altscreen_hook.c`: `alt_find_111`, `alt_setup`; `airplay_seams.c` callback | Type111 transport is prepared only after a Type111 request; failed setup is returned as error. | `honda-stream-type-dispatch.md`; `honda-setup-stream-identity.md` | Honda Type110 branch returns type 110/dataPort. Unsupported Type111 is logged/skipped, with no Type111 response entry in that branch. | `STATIC_HONDA_EVIDENCE` | Any other Type111 branch/descendant artifact and accepted transport/security contract. | Audi's listener, crypto and response are incompatible assumptions for Honda. |
| `altscreen_hook.c`: session-scoped advert owner and preflight | Hook retains a session-owned display/feature tree, invalidates stale setup generations, and rolls back if setup is not ready. | `honda-altscreen-gap-analysis.md`; `honda-session-finalizer-registration.md` | Honda stock owns its session and setup response. No accepted-feature owner or proven multi-subscriber extension mechanism is documented in reviewed evidence. | `STATIC_HONDA_EVIDENCE` | Supported per-session capability owner and lifecycle callback/API. | An internal post-Setup seam is not authority to take ownership or mutate production state. |
| Audi `extendedFeatures`/SETUP report; both Audi docs | Authors report iOS 26.6's precise activation predicate and sequence. | Honda Type111 differential and `honda-setup-stream-identity.md` | No Honda phone transaction or Type111-positive Honda artifact is established. | `AUDI_REFERENCE_ONLY` | Honda/iOS version-specific trace with authorized capture or equivalent source proof. | No claim that Type111 is enabled or that the same phone gate applies to MY16ADA. |
| No Audi symbol is a Honda API | Audi has its own interposition and receiver transport implementation. | Existing static audit notes; no Honda extension contract found | No documented extension mechanism located in the reviewed evidence. This is not a universal absence claim. | `UNKNOWN` | Honda-published developer API, authorized vendor interface, or complete supported extension specification. | Production capability injection is unsupported and must remain disabled. |

## Answers

| Question | Finding |
|---|---|
| A. Does Honda build a `displays` array? | Yes in the recovered `/info` path: a one-element array containing a main-display descriptor. `STATIC_HONDA_EVIDENCE`. |
| B. Stable main-display UUID? | It inserts a numeric UUID from `ScreenCopyMain()`. Stability/value provenance and semantic role are unknown. Not established. |
| C. Secondary descriptor? | None in the recovered builder; no loop/alternate source was recovered. Bounded static observation, not proof of global absence. |
| D. `extendedFeatures` constructed or consumed? | Not recovered; key/token literals are absent in the inspected ELF scan. Equivalent nonliteral behavior remains unknown. |
| E. Is request `features` received at control SETUP? | Setup receives a request dictionary and processes streams. No feature-token request processing was recovered. Do not conflate stream `features` display metadata with a SETUP proposal. |
| F. Is response `enabledFeatures` present? | No such insertion is recovered; exact key literal absent in the inspected binary scan. Do not claim universal absence. |
| G. What owns accepted feature set? | Unknown. The recovered Honda code creates a response with stock stream entries; no separate negotiated set/owner is documented. |
| H. Documented extension mechanism? | None found in reviewed notes. Existing internal callbacks/setters do not prove a public, chainable or authorized extension API. |
| I. Evidence needed for Type111 support? | Versioned authorized Honda spec or fully traced authorized implementation showing `/info` main+secondary descriptors and stable distinct IDs; SETUP request proposal parsing; accepted-feature response ownership; Type111 request dispatch, response with usable port, auth/crypto/framing, lifecycle/rollback; plus authorized compatibility evidence that the target phone actually requests the stream. A string match or Audi behavior is insufficient. |

## Verified path and boundary

```mermaid
flowchart LR
  P[Phone] -->|GET /info| H[Honda jmcs internal path]
  H --> M[ScreenCopyMain: one main descriptor]
  M --> D[displays array serialized]
  P -->|control SETUP request| S[Honda AirPlayReceiverSessionSetup]
  S --> T{streams[].type}
  T -->|110| O[stock Type110 setup and response]
  T -->|111 / unsupported| X[logged/skipped in recovered path]
  S -. no recovered accepted-feature set .-> U[UNKNOWN owner / no documented API]
  U -. no supported extension proven .-> D
```

The only verified path is the stock main-display and Type110 path in the inspected static artifact. Dashed edges are explicitly unknown; the chart does not claim Type111 advertisement or negotiation support.

## Independent offline contract fixtures

`tests/integration/test_cl_r9a_contract_fixtures.py` contains independently authored synthetic invariants. They require unchanged main identity, unique secondary identity, accepted features to be a subset of proposals and implemented capabilities, present `enabledFeatures`, matching session/generation owner, valid display shapes, and complete secondary transport readiness. Rejection raises a sanitized fixture error. These tests define a generic fail-closed model; they are not Honda values, Honda behavior, or a receiver implementation.

`safeForHonda()` remains false. No Honda production capability injection or receiver edits were made.
