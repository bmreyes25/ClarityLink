# CL-HONDA-111-01 / M2 — Honda receiver Type111 admission matrix

Offline, static, synthetic. `safeForHonda() == false`. Labels are defined in the [evidence map](cl-honda-111-01-evidence-map.md). Honda subject: `jmcs` SHA-256 `cbc7ba88…1c232`. Exact addresses and bodies stay private; function names below are the ones already published in the ClarityLink research notes cited in each row.

The columns answer the brief's test directly: **what already exists** in the factory receiver, **what ClarityLink could implement offline** without crossing an authentication boundary, and **what requires a verified authorization or session interface** that the preserved evidence does not provide.

## 1. Traced path (A1)

```
iPhone
 → USB / iAP2, factory authentication (owned by the factory process)
 → AirPlay-family receiver in jmcs (session object, master material)
 → HTTP /info  → _requestProcessInfo → AirPlayCopyServerInfo → displays[ one main descriptor ]
 → HTTP SETUP → AirPlayReceiverSessionSetup → streams[] loop
        100/101 → audio setup
        110     → screen setup: read streamConnectionID, derive key+IV, AES-CTR context,
                  bind(0) listener, response {type:110, dataPort}
        other   → log, continue (no status, no response change)
 → ScreenSession thread: accept, 128-byte header + body, CTR before opcode dispatch
 → opcode 0 → ScreenStreamProcessData → Android MediaCodec → platform video out → Display 0
 → opcode 1 → config path (avcC-like)
 ← mc_carplay_proxy_screen_register: one global callback set, one global flag
```

Evidence: `HONDA_STATIC_CONFIRMED` for every arrow above (CL-FACTORY-01 reports 03 and 05; Steps 32, 36, 38). The `/info` and SETUP bytes are produced and consumed inside `jmcs`; the Android services in front of it see only status callbacks.

## 2. `/info` and the second-display question (A2)

| # | Question | Finding | Class |
|---|---|---|---|
| 1 | Where does the stock receiver build `/info`? | `AirPlayCopyServerInfo` (`jmcs`), called from `_requestProcessInfo`; the same dictionary is passed to the binary-plist response writer, then released. | `HONDA_STATIC_CONFIRMED` |
| 2 | Does it have a representation of multiple screens? | The `displays` value is a mutable CF array, so the container can hold more than one dictionary. The builder appends exactly one, taken from the session's screen-property callback, which calls `ScreenCopyMain` once. | `HONDA_STATIC_CONFIRMED` (container) / `UNKNOWN` (support) |
| 3 | Is the descriptor hardcoded or generated? | Generated from the main-screen registry entry (index 0) and local configuration; fields `edid`, `features`, `maxFPS`, physical and pixel sizes, numeric `uuid`. | `HONDA_STATIC_CONFIRMED` |
| 4 | Can a secondary UUID be represented by existing models? | Not by the traced builder. Its `uuid` is inserted with a numeric setter and the builder has no second source. The external receivers use string UUIDs. A second descriptor would be a project-authored object, not an existing Honda model. | `HONDA_STATIC_CONFIRMED` / `INFERRED` |
| 5 | Is `extendedFeatures` or related capability data understood? | No. There is no `extendedFeatures`, `altScreen` or `viewAreas` literal. `features` is a masked integer with unknown bit meanings. The stock Audi 210.81 library has the same gap and the external hook injects the key. | `HONDA_STATIC_CONFIRMED` / `EXTERNAL_SOURCE_CONFIRMED` |
| 6 | Can the control session retain multiple screen identities? | The traced screen object, registry and proxy registration are single. The session-side field that holds the accepted screen is one slot. No multi-screen retention was found. | `HONDA_STATIC_CONFIRMED` (absence in traced paths) |
| 7 | Does the phone's decision to request Type111 depend on more than a second descriptor? | Per the only fetched production source, **yes**: the negotiated `altScreen` feature in both directions, at least two raw displays, a second identity distinct from display 0, and a well-formed `initialVideoStreams`. The same source reports a session teardown loop when the descriptor is malformed. All of this is the author's report about the phone, not a Honda result. | `EXTERNAL_AUTHOR_REPORTED`; Honda `UNKNOWN` |

**Do not assume appending a display dictionary is enough.** The unknown fields that remain: the accepted descriptor schema, the feature-token generation the phone expects from this receiver, the SETUP-side feature echo, `viewAreas` semantics, and whether this receiver's advertised protocol generation is high enough for the phone to offer a second stream at all.

## 3. Type111 SETUP (A3)

| Question | Answer | Class |
|---|---|---|
| Where is stream type dispatched? | Inside `AirPlayReceiverSessionSetup`, in the loop over `streams[]`, which reads `type` with an integer getter and branches. | `HONDA_STATIC_CONFIRMED` |
| Which layer owns the parsed request? | The HTTP connection handler in `jmcs` parses the property list and passes the request dictionary and a response out-pointer to Setup. Nothing outside `jmcs` receives it. | `HONDA_STATIC_CONFIRMED` |
| Who owns the authenticated parent session? | The factory process. The session object holds the 16-byte master material used by the Type110 KDF. No reviewed Android service exposes it. | `HONDA_STATIC_CONFIRMED` / `UNSUPPORTED` (no export) |
| Who owns the response serializer? | The caller of Setup, after Setup returns zero: it serializes synchronously, writes through the connection state machine and releases the response. | `HONDA_STATIC_CONFIRMED` |
| What Type111 behaviour is absent? | (a) a `/info` second descriptor and feature tokens; (b) a SETUP branch for 111; (c) a listener and data-port for it; (d) a KDF call and CTR context for it; (e) a response entry; (f) a screen object and callback registration for it; (g) a teardown branch for it. | `HONDA_STATIC_CONFIRMED` |
| Which existing structures are reusable? | The CF dictionary and array callback tables and the entry-append and release rules (full ledger recovered); the `bind(0)`/`getsockname` listener pattern; the screen KDF helper with its two 16-byte outputs; the AES-CTR primitive with its continuous-state semantics. | `HONDA_STATIC_CONFIRMED` |
| What does a legitimate receiver-owned secondary stream need? | Code that runs where Setup runs (inside `jmcs`), a stock-first call so Type110 is untouched, an independent listener, KDF output and CTR context, an independent teardown owner, and a response entry appended to a copy of the stock response. The brief's candidate 1 and the external hooks have this shape. | `INFERRED` from `EXTERNAL_SOURCE_CONFIRMED` + Honda ownership ledger |
| Which actions would affect Type110 state? | Anything touching the screen object's CTR context (shared advancing counter), the proxy's single registration, the `streams[]` array handed to teardown, the response array, or the HTTP failure path. A secondary design must therefore avoid all five. | `HONDA_STATIC_CONFIRMED` |
| What supported or authorized extension boundary exists? | **None found.** No exported Binder, plugin registration, configuration key, delegate or documented interposition seam exists for `jmcs`. A reachable internal function is not an extension API. | `UNSUPPORTED` in reviewed evidence |

Mixed-request behaviour, statically: `[110,111]`, `[111,110]`, `[111]` all succeed at the transaction level with no Type111 entry. Rollback on a supported-stream failure tears down earlier supported streams but gives Type111 no cleanup. Phone behaviour on a response that omits a requested 111 is `UNKNOWN`.

## 4. Authentication and security context (A4)

| ID | Item | Honda | Reusable by a child stream? | Class |
|---|---|---|---|---|
| S1 | iAP2 / MFi authentication | Entirely inside the factory stack. This campaign neither touches nor emulates it. | Not exportable. A child stream must be authorized *by* the parent, never authenticate itself. | `UNSUPPORTED` |
| S2 | Authenticated parent session object | Passed into Setup. | Only code running in the factory process can use it. | `HONDA_STATIC_CONFIRMED` |
| S3 | 16-byte master material | Read by the Type110 KDF call. | Whether Type111 uses the same material is `UNKNOWN`. It must never be copied out of the process or logged. | `HONDA_STATIC_CONFIRMED` / `UNKNOWN` |
| S4 | `streamConnectionID` | Peer-supplied, nonzero uint64, read in the 110 branch, formatted as unsigned decimal ASCII in the salts. | A Type111 entry carries its own ID in every external source; Honda's 111 request shape is unseen. | `HONDA_STATIC_CONFIRMED` (110) / `UNKNOWN` (111) |
| S5 | Type110 KDF | `SHA-512(salt ‖ master)` truncated to 16 bytes, salts `AirPlayStreamKey%llu` and `AirPlayStreamIV%llu`. Modelled offline in `screen_kdf.py` with synthetic bytes. | **Classified separately from Type111.** | `HONDA_STATIC_CONFIRMED` |
| S6 | Type111 key derivation | No Honda call. Project B calls the *same named function* on the Audi stock library with the session AES key and the 111 stream's own ID. | `LEGACY_PER_SCREEN_KDF_STRONGLY_SUPPORTED` as a lead; **Honda unproven**. Not implemented, not defaulted. | `EXTERNAL_SOURCE_CONFIRMED` / `UNKNOWN` |
| S7 | Modern profile (HKDF + ChaCha20-Poly1305, 8-byte counter) | Absent from Honda. | Do not port into Honda. Kept only as a synthetic profile. | `EXTERNAL_SOURCE_CONFIRMED` |
| S8 | Stream-protection scope | Honda Type110: whole body of every opcode passes through one CTR context, header clear. Audi 111: opcode 1 clear, opcode 0 CTR. Modern: config clear, frames AEAD. | Policy for Honda Type111 `UNKNOWN` (evidence-map C2). The legacy ClarityLink profile fails closed on opcode 1. | conflict kept |
| S9 | CTR context isolation | One CTR context per stream; reusing the Type110 context would advance and corrupt both. | Required design rule for any child stream. | `HONDA_STATIC_CONFIRMED` + design |
| S10 | Key lifetime | Honda zeroes its temporary key and IV after installation and finalizes the context on teardown. | A child must do the same; a Python model can only best-effort zero. | `HONDA_STATIC_CONFIRMED` + design |

**Can the factory receiver keep authentication inside the original owner and still authorize a child?** The structure supports it: the parent session, the master material and the Setup transaction all live in one process, and the Type110 branch already shows the KDF-and-context pattern per stream. Whether a Type111 child *may* use that material, and how, is a decision for the factory code's owner, not something the preserved artifacts can answer. The preserved evidence supplies no sanctioned way to ask the factory code to authorize an additional stream, so this stays `UNSUPPORTED`.

## 5. The matrix

| # | Capability needed for a receiver-owned Type111 child | Exists in the Honda factory receiver | ClarityLink offline status | Needs a verified authorization / session interface |
|---|---|---|---|---|
| 1 | Advertise a second display in `/info` | Container yes, builder no, tokens no | Display-descriptor models, `external_alt_screen.py`, capability planning (`SYNTHETIC_TESTED`) | **Yes**: a supported way to extend the factory's `/info` output and the exact descriptor and feature schema |
| 2 | Accept `type:111` in SETUP | Branch skipped | Contract, parser, duplicate-ID rejection, once-only serializer, rollback (`SYNTHETIC_TESTED`) | **Yes**: a supported way to run code at that branch without altering Type110 |
| 3 | Call stock Setup first, append to a copy of its response | Response ownership ledger recovered | Augmentor and response-delivery models (`SYNTHETIC_TESTED`) | **Yes**: a hook seam in the factory process |
| 4 | Independent listener and data port | `bind(0)` pattern exists for 110 | `HostListener` lifecycle (`SYNTHETIC_TESTED`) | **Yes**: phone reachability and process ownership |
| 5 | Parent authority revoked on parent loss | Session teardown exists; 111 gets no branch | Parent-to-child revocation (`SYNTHETIC_TESTED`) | **Yes**: a parent-loss signal a child can subscribe to; the existing destroyed-event is a single global callback slot with no session identity |
| 6 | Independent security context | KDF helper and CTR primitive exist | Provider interface, fail-closed `EvidenceRequiredSecurity`, synthetic AEAD (`SYNTHETIC_TESTED`) | **Yes**: authorization from the parent to derive; the Type111 KDF and profile are `UNKNOWN`; no guessed default |
| 7 | VideoConfig handling | Type110 config path exists, CTR-protected | AVCC parsing, replacement, restart (`SYNTHETIC_TESTED`); legacy profile fails closed | **Yes**: a real session to settle clear versus protected |
| 8 | Decode and frame handoff | MediaCodec path exists for 110, singleton proxy | Host decode, `FrameGate`, generation-gated dispatch (`SYNTHETIC_TESTED`) | **Yes**: a second decoder-and-sink registration the proxy does not offer |
| 9 | Per-stream teardown that leaves Type110 intact | 110 only | Secondary teardown leaves primary (`SYNTHETIC_TESTED`) | **Yes**: a teardown branch for 111 |
| 10 | Type110 continuity proof | Understood statically | Isolation scenarios (`SYNTHETIC_TESTED`) | **Yes**: a real simultaneous session |

Rows 1–10 give the same answer: everything ClarityLink can build is the *consumer* side of a contract whose *provider* side does not exist outside the factory process.

## 6. What could still be implemented offline (feeds M3)

Only items that do not need an unknown fact and are not already covered:

1. **A Type111 child-stream authority object** that makes the parent-to-child relationship a single explicit contract: bound to one parent generation, one stream identity and one security-grant slot; revoked by the parent; incapable of outliving it; unable to reach Type110 state. Existing pieces enforce this piecemeal across `Receiver`, `PresentationStreamCoordinator` and the pipeline; a single reusable object that the display integration can require is missing.
2. **A pane-lease contract** on the display side (see the [Navigation-pane contract](cl-honda-111-01-navigation-pane-contract.md)).
3. **Policy tests that pin the fail-closed answers** above: legacy opcode 1, unknown KDF, unattested grant, no default descriptor fields.

Nothing here implements a guessed KDF, a fake authentication success, an `ATTESTED` path or a Honda-facing call.

## 7. Verdict for Gate 1

`UNSUPPORTED` entry point; `NO-GO` for any active work. See the [critical boundaries](../../docs/development/cl-honda-111-01-critical-boundaries.md).
