# Honda / xcertplay / DiPlay / PlayPort Type111 differential

## Evidence boundary

Honda column is from the hash-matched `jmcs` static reports cited below. xcertplay is pinned to `17c92439413638dfd1d7f91d7e1c2e7358398762`; DiPlay to `f2d06951b4e8114dbb62f551c12a32a845a3042f`; PlayPort to `9a0882dd0ffe48e467b59d58b12d81391df55ade`. External implementation agreement remains `EXTERNAL_PRIOR_ART`; DiPlay's maintainer report of physical iOS 27 cluster rendering is separately `EXTERNAL_PHYSICAL_VALIDATION`. DiPlay and PlayPort share ancestry/code with xcertplay, so agreement is not claimed to be fully independent. Nothing external changes Honda's Type111 status.

## Display and `/info`

| Field / behavior | HONDA | XCERTPLAY | DIPLAY | PLAYPORT | Confidence | Portable to ClarityLink? / notes |
|---|---|---|---|---|---|---|
| `displays` array | One main descriptor built by recovered path | Main plus optional configured cluster | Main plus optional cluster | Optional cluster in protocol config; default server omits it | Honda confirmed; external prior art | Keep Honda Type110 object; second descriptor is a separate unproven Honda `/info` change. |
| Primary display | `ScreenCopyMain()` main-screen path | Type 110 | Type 110 | Type 110 | Honda confirmed / external prior art | Type 110 identity is useful protocol reference, not a new Honda behavior. |
| Secondary display | No second descriptor in inspected builder | Optional type 111 | Optional type 111 | Optional type 111 plumbing, disabled by default | Honda confirmed absence in bounded builder; external prior art | Candidate architecture only. |
| `type` 110 / 111 | Type110 Setup confirmed; descriptor `type` only indirect candidate; stock Type111 Setup unsupported | Constants and display entries 110/111 | 110/111 | 110/111 | Mixed | Preserve stock Type110; 111 remains project candidate. |
| Display UUID | Numeric setter in Honda descriptor; meaning unresolved | Distinct fixed main/alt UUID strings | Distinct display UUIDs | Separate display UUIDs in protocol profile | Honda confirmed encoding / external prior art | Do not copy external UUIDs or assume Honda UUID joins stream identity. |
| Pixel dimensions | Honda main fields confirmed, runtime values config-backed | Per-display config | Per-display config | Per-display config | Mixed | No secondary geometry selected; use unknown until measured/approved. |
| Physical dimensions | Honda main fields confirmed | Config or generated ratio | Config/profile geometry | Config/profile geometry | Mixed | No external numeric value portable as a Honda setting. |
| `maxFPS` | Honda main field confirmed | Per-display configured/sanitized FPS | Per-display configured profile | Per-display configuration | Mixed | Candidate field only; rates require evidence. |
| Display `features` | Honda field confirmed; bit meanings unknown | Emitted from implementation flags | Cluster profile uses its selected flags | External profile | Mixed | Preserve Honda value and semantics; no external bit copying. |
| `primaryInputDevice` | Not found as a literal in bounded Honda builder | Included per display; configurable | Cluster profile sets noninteractive value | Present via inherited protocol model | External prior art | Single external field support; Honda requirement unknown. |
| `viewAreas` | Not found in inspected Honda builder | One area emitted, with nested safe area | View and safe-area geometry | Inherited protocol support | External prior art | Multi-implementation candidate; exact geometry/profile is not portable. |
| `initialViewArea` | Not found in inspected Honda builder | `0` | `0` in cluster profile | External profile | External prior art | Common code pattern, still Honda unknown. |
| `safeArea` | Not found in inspected Honda builder | Nested in `viewAreas` | Cluster safe-area behavior configured and documented | Inherited protocol support | External prior art; DiPlay adds vehicle report | Geometry and draw-outside behavior remain profile-specific. |
| `initialURL` | Not found in inspected Honda builder | Optional config field | Cluster map URL selected in tested profile; docs report absent value produced black frame there | Optional inherited config | External prior art; physical result only DiPlay report | Do not assume required on Honda. |
| Phone `altScreenURLs` | Honda request behavior unknown | No reader/trace found in audited files | Source/docs handle URL candidates and document Maps URL family | Not established by inspected default PlayPort server | External prior art, partial | Current iPhone behavior still belongs in isolated oracle; no phone capture here. |

## SETUP negotiation and stream responses

| Field / behavior | HONDA | XCERTPLAY | DIPLAY | PLAYPORT | Confidence | Portable to ClarityLink? / notes |
|---|---|---|---|---|---|---|
| Requested features | Honda request path is parsed; Type111-specific requested feature requirement unknown | No current-phone capture asserted | Handles candidate features/URLs | Protocol path carries setup request | External evidence incomplete | Observe only in PlayPort oracle; do not fabricate request values. |
| Returned `enabledFeatures` | Honda response path known; Type111 tokens unknown | Always includes `viewAreas`, conditionally `altScreen` for cluster | `viewAreas`, conditional `altScreen` | Similar inherited behavior | Multiple implementation agreement | Candidate only; minimum iOS-required set unknown. |
| `viewAreas` / `altScreen` tokens | Honda Type111 requirement unknown | As above | As above | As above | External prior art | Do not add until Honda/iPhone evidence supports. |
| SETUP streams | Honda iterates request streams; Type110 accepted; Type111 skipped | 110 and 111 dispatched independently | 110 and 111 dispatched independently | 110 and 111 protocol plumbing | Honda confirmed + external prior art | Read-only inspect; keep original request unchanged. |
| Type110 response | `{type:110,dataPort}` stock path | `{type,dataPort}` | `{type,dataPort}` | `{type,dataPort}` | Honda confirmed + external prior art | Stock Honda Type110 stays on original path. |
| Type111 response | No stock response entry | `{type:111,dataPort}` when accepted | `{type:111,dataPort}` when accepted | `{type:111,dataPort}` when accepted | External prior art | Clean-room candidate only; response extension must be separately gated. |
| `dataPort` | Honda Type110 listener port confirmed | Independent screen listener's bound port | Independent listener's bound port | Independent protocol listener | External prior art / Honda 110 confirmed | Ordering candidate: listener established, actual port obtained, then response entry. Honda Type111 not proven. |
| `streamConnectionID` | Honda Type110 ID feeds legacy screen crypto | Per-stream ID feeds DataStream key derivation | Similar modern path | Similar modern path | Mixed | Distinct per stream is a candidate; never reuse or log real secret values. |

## Control, transport, and security

| Field / behavior | HONDA | XCERTPLAY | DIPLAY | PLAYPORT | Confidence | Portable to ClarityLink? / notes |
|---|---|---|---|---|---|---|
| `forceKeyFrame` with no UUID | Honda symbol/string evidence unresolved | Type110 helper sends empty params, primary target | Primary behavior plus separate cluster path | Similar inherited primary behavior | Mixed | xcertplay supports only primary recovery at this pin. |
| UUID-scoped alternate keyframe | Honda unknown | Not found; no Type111 recovery callback installed | Added for alternate UUID | Present in inherited implementation | External prior art, DiPlay-specific extension | Do not attribute to xcertplay or Honda. |
| `showUI` / `stopUI` | Honda unknown | Not found in inspected source | UUID-scoped cluster UI operations | Inherited project behavior where present | External prior art, DiPlay extension | Not Honda requirements. |
| 128-byte header | Honda Type110 confirmed | Documented in `ScreenStream` | Documented | Inherited | Honda Type110 + external prior art | Likely framing-family invariant only; Honda Type111 remains unknown. |
| VideoFrame / VideoConfig | Honda parser's legacy frame/config handling confirmed for Type110 | Opcode 0/1 | Opcode concepts | Inherited | Mixed | Protocol concepts align externally; Type111 interpretation not Honda-proven. |
| H.264 framing | Honda legacy screen path confirmed | Length-prefixed NALs converted to Annex-B | Length-prefixed media path | Similar protocol path | Mixed | Don't treat all codec/HEVC behavior as invariant. |
| Encryption | Honda Type110 SHA-512 derivation + AES-CTR | DataStream HKDF + ChaCha20-Poly1305 | Modern DataStream key + ChaCha20-Poly1305 | Same implementation family | Honda confirmed 110; external modern prior art | Never port modern cipher to Honda. Honda 111 unknown. |
| Key derivation | Honda Type110 session master material and stream ID | Shared secret + streamConnectionID/DataStream labels | Similar modern derivation | Similar modern derivation | Mixed | Type111 session security is a high-priority Honda-specific unknown. |
| Stream identity | Honda Type110 session/stream behavior confirmed; Type111 absent | `(session,type)` media key | Separate 110/111 | Separate 110/111 and type carried through web wire | External prior art | Project should key `(opaque session, generation, stream type)` without mutating Honda state. |

## Clean-room candidate schema

`src/claritylink-negotiation/external_alt_screen.py` defines `Type111CandidateDisplay` and `Type111CandidateSetup` with per-field provenance: `HONDA_CONFIRMED`, `MULTIPLE_EXTERNAL_PRIOR_ART`, `SINGLE_EXTERNAL_PRIOR_ART`, or `UNKNOWN`. The external candidate factory rejects `HONDA_CONFIRMED`, and leaves Honda status `HONDA_UNKNOWN` for every field. Multi-implementation agreement means code agreement across inspected projects; source ancestry overlaps and is explicitly not treated as independent experimental confirmation. Chosen geometry, UUID, stream ID, and port remain unset rather than borrowing external constants.

## Prior-art source map

- [xcertplay pinned differential](xcertplay-type111-differential.md)
- [DiPlay pinned differential](diplay-type111-differential.md)
- [PlayPort pinned differential](playport-type111-differential.md)
- [Honda security comparison](honda-vs-modern-type111-security.md)
- [PlayPort oracle plan](../lab/playport-type111-oracle-plan.md)

High-value Honda-specific unknowns remain: can Honda instantiate separate screen security for a second stream ID; what is the minimum current-phone feature set; can an independent project listener coexist with stock Type110; and where can the Type111 stream reach the instrument-cluster renderer? Existing trampoline target remains `0x28afba`.
