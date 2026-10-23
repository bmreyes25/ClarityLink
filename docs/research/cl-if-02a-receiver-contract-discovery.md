# CL-IF-02A: Honda factory Type111 receiver contract discovery

**Phase 2 (receiver contract). Codex owns Phase 3 (cluster display) separately.**
Offline, static, documentation-level. No vehicle, Honda ADB, live iPhone, receiver patching, private API call, secret extraction or CAN activity occurred. `safeForHonda() == false`. Base `origin/main` `25e9b70c837f8d0e4840de9f20cf1e109e395bbc`. Exact addresses, symbols, evidence IDs and decompiled bodies stay in private storage.

## Receiver decision

**`NO_SUPPORTED_PATH_FOUND_IN_REVIEWED_SCOPE`**, and the gate stays **`RECEIVER_AUTHORIZED_SPEC_REQUIRED`**.

No documented, authorized, externally callable boundary was found that would let a client obtain an independent Type111 child stream under the existing authenticated session while Type110 stays independently owned. Every working external Type111 implementation reviewed uses unsupported binary interposition inside the receiver process. Nothing here proves the idea impossible: the only place a sanctioned seam could exist is the receiver integrator's own licensed SDK integration, which this repository does not hold and cannot read (see "Authorization still required").

## 1. New findings versus already-known

Already established (not repeated as discoveries): authentication lives in the stock receiver; `jmcs` builds `/info` with one main-screen descriptor; SETUP handles Type110 and skips Type111; no documented child-stream grant; the lab models Type111 synthetically (PR #80 admission matrix `research/honda/cl-honda-111-01-receiver-admission-matrix.md` on branch `claude/cl-honda-111-01-factory-receiver`, not yet on main; CL-AUTH-01 PR #78).

New in this campaign:

| # | Finding | Class | Bears on |
|---|---|---|---|
| N1 | The receiver is built on the standard AirPlay receiver SDK structure, with a **server delegate (control, property get/set, session created/failed) and a session delegate (initialize, finalize, control, property get/set, mode change, UI request, audio duck/unduck)**. These are the SDK's platform-adapter seam. They are installed once, internally, when a session is created. None of the callbacks is a stream-SETUP, stream-grant or display-registration hook. | `HONDA_STATIC_CONFIRMED` (Ghidra, hash-matched `jmcs`) | A, D |
| N2 | The delegate seam is **compile-time, OEM-owned**: it is wired inside the receiver binary. There is no registration entry point reachable from another process. So the only "documented receiver delegate" in the stack is a design-time integration point for the integrator, not an extension API for a third party. | `HONDA_STATIC_CONFIRMED` / `INFERRED` | A, D |
| N3 | The receiver has a **settings/preferences file mechanism** (SDK settings accessor, reloadable at runtime). Exactly two consumers exist: the device-name getter and the server-preferences updater. The updater reads only server enable, Bonjour disable, deny-interruptions, device name, overscan override, QoS disable and a data timeout. **No display, feature, stream or protocol-generation key.** The file itself is not in the preserved artifact set, so its contents are unverified, but no reader could use it for Type111. | `HONDA_STATIC_CONFIRMED` (readers) / `UNKNOWN` (file contents) | B |
| N4 | The only dynamic-library loads in `jmcs` are four fixed-purpose initializers: Bluetooth, the MFi platform, an audio utility library and the screen utility library (the known proxy). **No generic plugin or extension loader.** | `HONDA_STATIC_CONFIRMED` | A |
| N5 | The Android-to-receiver control vocabulary handled inside `jmcs` covers reference retain/release, callback registration, UI request, Siri request, mode change, night mode, limited UI, log control and emergency-call audio/guidance. **There is no display, screen, stream-grant or capability handler.** The Java layer (CL-FACTORY-01 note) carries no Type110/111/second-screen token. | `HONDA_STATIC_CONFIRMED` | A, C, D |
| N6 | The display-descriptor builder has a single caller; the screen-property path and the proxy's single callback registration are unchanged from the PR #80 reading. No second registration point appears in the new reachability checks. | `HONDA_STATIC_CONFIRMED` | B, D |
| N7 | External fact worth recording for Type110 continuity: the iPhone reads `/info` **once per session** and builds all display and stream configuration from that snapshot (no re-fetch). One project fabricated a main-display identity in its advertisement and this **blackened the stock main stream** until it reused the receiver's real identity and refused to advertise if the real one was missing. Any advertisement change is therefore a Type110 risk, not only a Type111 feature. | `EXTERNAL_AUTHOR_REPORTED` | B, Type110 |
| N8 | No verified Honda or supplier firmware/version documentation was found describing secondary CarPlay support or ruling it out. The preserved set contains binaries only, no integrator documentation. | `UNKNOWN` | E |

## 2. External project and version comparison

Sources read at public interface and documentation level only. No GPL-3.0 code was copied or transplanted, and nothing was fetched into the repository. Hardware results are author-reported.

| Project | Pinned revision | Licence | Target | Mechanism | Reported status |
|---|---|---|---|---|---|
| `luka-dev/mib2q-carplay-rgi` | `a63d5474…` | GPL-3.0 | Audi MHI2Q (QNX, stock airplay library 210.81) | Preload hook inside the stock process; external renderers | Production, car-tested by author; asks for latest regional firmware; only one cluster mod may own the cluster |
| `harman-f/mhi2_altscreen_carplay` | `30caa2ed…` | GPL-3.0 | VW Group MHI2 (reference: one MU1440 Škoda unit) | Inline prologue hooks on stock Setup/Start/TearDown/Control after plain preload proved insufficient on that unit | "Experimental research software"; one reference firmware only; other units explicitly not assumed; a different hash is a stop condition |
| `edzenis/mib2high-carplay-altscreen-rgi` | `bfea8685…` | Per component, not a blanket grant | Audi MIB2 High, one Q7 firmware | Altscreen receiver plus renderer | Stable on the single tested platform; other cars/firmware not supported |
| `lipedesign/mib3-moi3-altscreen` | `455658b0…` | MIT | VW MIB3 MOI3 LG | Preload hook | **Alpha, never confirmed on real hardware** |
| `shilapi/xcertplay` | `1298fb35…` (repo moved on from the earlier pinned `de9647f4…`) | GPL-3.0 | Android head unit receiver (not a factory unit) | Project-owned receiver | Modern generation; a descriptor-format reference only |

Per-interface comparison (all `EXTERNAL_SOURCE_CONFIRMED` or `EXTERNAL_AUTHOR_REPORTED` for those projects, never Honda):

| Interface | What the references show | Honda implication |
|---|---|---|
| 1. Secondary-display advertisement | A second display descriptor with its own identity is injected into `/info` by the hook, not supplied by a vendor option. | Honda builder has one source; injection is interposition. |
| 2. Alt-screen feature negotiation | Capability must be advertised and the phone must offer a second stream; the same feature token is echoed in SETUP. Malformed descriptors reported to cause teardown loops. | Honda feature tokens and phone offer unknown. |
| 3. Type111 SETUP | Stock Setup runs first, its response is kept, descriptors are cloned to keep unknown peer fields, and a project-owned entry with a data port is appended. | Response schema for Honda unknown; no guessing. |
| 4. Stream identity / transport | Own listener and port per secondary stream, reachable on the phone link (one project also needed a host firewall allowance). | Honda process ownership and reachability unknown. |
| 5. Parent authentication | Reuse of the already-authenticated session's material via an in-process observation seam plus the secondary stream's own connection identity; no second login. | The same trick requires running inside `jmcs`; not a contract. |
| 6. VideoConfig / protection | Legacy generation: config clear, frames AES-CTR; modern generation: AEAD. Projects warn not to substitute across generations. | Honda Type111 profile unknown. |
| 7. Type110 continuity | Primary left stock; secondary state separate; real main identity must be reused. | Matches PR #80 design rules. |
| 8. Teardown / revocation | Per-stream teardown, generation counters, fail-closed when hooks cannot install; source-session teardown vs. writer loss reported as unresolved by one project. | Honda has no Type111 teardown branch. |
| 9. Documented limits | Hash-gated, single-firmware, hardware-specific; "same model family" is not evidence. | Honda needs its own exact-hash evidence. |

Conclusion: the references establish that **a stock-first interposition design works on those units**, which is the same inference as before. They add no supported-API evidence, and they reinforce that adoption is per exact firmware hash.

## 3. Honda interface and permission matrix

Question key: A receiver extension interface, B advertisement source, C session delegation, D stream ownership, E compatibility documentation.

| Candidate | Q | Evidence source (hash-matched) | Documented / authorized? | Owner and caller permission | Grants authenticated-session access? | Type110 independent? | Externally callable without privileged injection? | Revocation / cleanup | Status |
|---|---|---|---|---|---|---|---|---|---|
| Server and session delegates (SDK platform adapter) | A, D | `jmcs` static | Not documented in preserved set; SDK documentation is not held | Receiver integrator, compile-time | Indirectly (runs in-process) | Unaffected by itself | No (no registration entry) | None for streams | **Private/internal, design-time** |
| Settings/preferences file | B | `jmcs` readers; file absent from preserved set | No | Whoever can write the file; unverified | No | n/a | Possibly, but no display or feature keys are read | n/a | **Ruled out for displays in reviewed scope** |
| Dynamic library loading | A | `jmcs` static | No | Receiver | n/a | n/a | No generic loader | n/a | **Ruled out (fixed-purpose only)** |
| Android control vocabulary into `jmcs` | A, C, D | `jmcs` static; Java AIDL (CL-FACTORY-01) | Not documented | Platform services | No | n/a | No display/stream handler exists | n/a | **Ruled out for secondary streams** |
| Proxy screen callback registry | D | Proxy library static | No | Receiver | No | Single global registration | No | n/a | **Private/internal; single slot** |
| Android Binder services (CarPlay, cluster, navigation) | A | Deodexed Java (CL-FACTORY-01) | Not documented | Platform; caller permissions unreviewed in this pass | No session or key export | n/a | Not a stream interface | n/a | **Not a Type111 interface; cluster side is Phase 3** |
| Interposition at Setup / `/info` (external pattern) | A–D | External projects only | Not authorized; not an extension API | Whoever injects | Yes, in-process | Must be proven | Requires privileged injection | Must be built | **Hypothetical; forbidden under project rules** |
| Vendor or Honda documentation for secondary CarPlay | E | None found | n/a | n/a | n/a | n/a | n/a | n/a | **Unknown** |

An internal function or hookable location is not a supported extension API.

## 4. Evidence classification and sources

| Claim | Class | Source |
|---|---|---|
| Delegate structure, settings readers, library-load callers, control vocabulary | `HONDA_STATIC_CONFIRMED` | `jmcs` hash `cbc7ba88…1c232`, re-verified this campaign; Ghidra 12.1.4 via REA; private evidence IDs held in private notes |
| Java layer carries no second-screen tokens | `HONDA_STATIC_CONFIRMED` | CL-FACTORY-01 private M2 note |
| Hash gating, stock-first design, `/info` once per session | `EXTERNAL_SOURCE_CONFIRMED` / `EXTERNAL_AUTHOR_REPORTED` | Pinned repositories above |
| Search for Honda secondary-CarPlay documentation | negative result | Preserved artifact set (377 hashed entries) contains no integrator documentation |

The settings-file contents, caller permissions on the Binder services and any integrator SDK documentation are not covered by this pass.

## 5. Missing receiver contract fields

All remain `UNKNOWN` and are not guessed: the accepted second-display descriptor schema and feature-token generation; whether the receiver's protocol generation makes the phone offer a second stream; Type111 SETUP request and response shape; key-derivation inputs and protection profile (including whether VideoConfig is protected); string versus numeric display identity; independent listener ownership and reachability; child-stream revocation signal; per-stream teardown; Type110 continuity under the added advertisement.

## 6. Can additional offline evidence resolve the gaps?

- **Yes, narrowly:** (a) the contents of the receiver settings file, if a lawful preserved copy exists (a copy of the system image tree, not a car read); it can only confirm that no display key exists. (b) Caller-permission and exported-component review of the CarPlay and cluster Binder services in the existing deodexed set, to close the "caller permissions" column. Both are low information gain for Type111.
- **No:** the SETUP schema, KDF, protection profile and phone behavior cannot be derived from stock binaries, because stock code does not implement them. Further disassembly of the Type110 path would repeat PR #80.

## 7. Would a passive observation help?

A single parked, read-only capture of the existing `/info` response from a normal Type110 session would show the actual advertised feature tokens, protocol generation and descriptor shape, which are the first unknowns. It would **not** show Type111 behavior, and it needs separate owner authorization for a specific non-vehicle-modifying procedure (the current campaign rules forbid car access). Present recommendation: not needed now; the documentation route below should come first, and a car observation does not materially help until a supported interface exists.

## 8. Authorization and documentation still required

1. Written confirmation from the receiver integrator or Honda that a supported mechanism exists (or does not) for a third-party client to obtain an additional CarPlay display stream, plus its interface description, caller authorization model and applicable firmware versions.
2. If a mechanism exists: the child-stream grant contract (authentication relationship, key derivation owner, revocation signal, teardown), and the Type111 SETUP and `/info` schema for this receiver's generation.
3. Owner authorization for any parked passive observation, naming the exact procedure.

### Inquiry draft (not sent; no contact without separate authorization)

> For the [model year] [model] factory display audio receiver, firmware [exact version]: (1) Does the CarPlay receiver support an additional (instrument-cluster / alternate-screen) display stream? (2) If so, is there a documented or licensed interface for an authorized accessory to receive it without modifying the receiver? (3) Which protocol generation does the receiver advertise, and does it include alternate-screen negotiation? (4) How is the additional stream's authorization derived from the authenticated session, and what revokes it? (5) Is the receiver's Type110 stream guaranteed independent of it?

Maintainer questions (GPL projects, public issue tracker or discussions only): which exact firmware and library hashes were tested; what the phone's offer depends on beyond the advertised second descriptor; whether the Type111 entry in SETUP was accepted without the feature echo; what happens to the primary stream when the secondary fails.

## 9. Self-review and verification

Independent review: **outstanding** (`@ECC` was not callable from this environment). Self-review: all rows checked against the private notes; no addresses, symbol bodies, evidence IDs, keys or paths to private trees appear here. Static analysis only; REA session closed; source-immutable.
