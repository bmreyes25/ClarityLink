# CL-HONDA-111-01 / M1 — Consolidated evidence map

Offline, static, synthetic work only. No vehicle, Honda ADB, live iPhone, hardware provisioning, credential access or injection occurred. `safeForHonda() == false`; `safe_for_honda() == False`. Base: `origin/main` `b9fa1a0b4aae11f71b257c3b7729470c5a8dc792`.

This map reconciles the preserved Honda, HondaHack, external-reference and ClarityLink evidence for the single question in the campaign brief. It does not erase historical provenance: where two sources disagree, both rows stay and the conflict is named (section 3). Exact addresses, symbols, hook targets and decompiled bodies stay in private storage; this document is role-level and cites public ClarityLink reports.

## 1. Evidence labels used

| Label | Meaning |
|---|---|
| `HONDA_STATIC_CONFIRMED` | Read from a hash-matched Honda artifact (jmcs ELF, deodexed Honda services). Static only. |
| `HONDA_PRIOR_RUNTIME` | Saved read-only observation from an earlier authorized session (Display 1 captures, WindowManager/SurfaceFlinger dumps, Test 4C footage). Not re-collected here. |
| `HONDAHACK_STATIC` | Read from the preserved HondaHack 7.7.7 APK (`5013b478…afb73`). |
| `HONDAHACK_PRIOR_RUNTIME` | HondaHack behaviour seen in the saved Honda captures. |
| `EXTERNAL_SOURCE_CONFIRMED` | Read directly from a pinned public source tree in this campaign. The source says so; no vehicle result is implied. |
| `EXTERNAL_AUTHOR_REPORTED` | A claim in a README, comment or issue that this campaign did not verify. |
| `SYNTHETIC_TESTED` | ClarityLink offline model or test. Never promoted to Honda evidence. |
| `INFERRED` / `UNKNOWN` / `UNSUPPORTED` | As in the brief. `UNSUPPORTED` means a supported interface was looked for and not found, not that the idea is impossible. |

## 2. Subjects and pins

| Subject | Pin | Role | Licence |
|---|---|---|---|
| Honda `jmcs` (CarPlay receiver) | SHA-256 `cbc7ba88…1c232` | Type110 reference, SETUP / `/info` / KDF | Proprietary, private |
| Honda ExternalDisplay Out/Ap services, Navigation, CarPlay APKs | deodexed set under CL-FACTORY-01 private storage | Display 1 host, navigation to cluster | Proprietary, private |
| HondaHack 7.7.7 | SHA-256 `5013b478…afb73` (re-verified this campaign against the private copy) | Cluster casting reference | Proprietary, private |
| Project B `luka-dev/mib2q-carplay-rgi` | `a63d54741839c7d30d32dd4e149f693856bcb0db` | Audi MHI2Q stream 111 (QNX, stock libairplay 210.81, `LD_PRELOAD`) | GPL-3.0 |
| Project C `harman-f/mhi2_altscreen_carplay` | `30caa2eddf9a697c217028f8b55c1e3bdef70643` (earlier ClarityLink audit pinned `c2f811f1…`) | MHI2 stream 111 interposer | GPL-3.0 |
| Project D `edzenis/mib2high-carplay-altscreen-rgi` | `bfea86859a5bdaed3c29a16f03fc7ba87ef4a19e` | MIB2 High cluster map, VIEW-button layout following | Per component; root licence is not a blanket grant |
| Project I `f-io/LIVI` | `91f7ced80c6a3bac60af4198c9e85e5a1b03f58d` (default branch); see the [upstream currency check](../runtime/cl-auth-01-livi-upstream-currency.md) | Authentication-boundary comparison only. Not a dependency. | GPL-3.0 |
| `alexpotv/Clusters` (Civic) | `2b9844e4c174df281de99e8e084ae7ee52ad1f61` | Private vendor-service technique on a different car | None declared |
| PlayPort, DiPlay, xcertplay | see `research/carplay/*-differential.md` | Modern Type111 receivers | Per project |

## 3. Contradictions and stale claims, resolved or kept open

| # | Conflict | Sources | Resolution |
|---|---|---|---|
| C1 | **Is the HondaHack display-host identity resolved?** The HondaHack-Research private repo records U-13 (hook targets, `InterfaceWindow`, `getMainLayout/getInterruptLayout`, the external-display package) as `UNRESOLVED` because the APK encrypts its string constants. ClarityLink reports name these targets as known. | HondaHack-Research `docs/UNKNOWNS.md` U-13 vs `research/hondahack/hondahack-display-path.md` | Both are true of different methods. This campaign re-checked the preserved APK (hash matches) and found **zero cleartext occurrences** of the host class, accessor or package names in its DEX. The ClarityLink names come from a separate static string decoder (`research/scripts/decode_hondahack_strings.py` in the private analysis checkout) that used bytes from a backed-up Xposed `app_process` to recover 283 names. Class: `HONDAHACK_STATIC` via an external decode, **not independently reproduced here**. The names agree with the Honda host's own preserved source (`HONDA_STATIC_CONFIRMED` for the host classes and methods), which is the strongest cross-check available. Keep both statements; do not call U-13 closed in HondaHack-Research until the decoder is reproduced there. |
| C2 | **Is VideoConfig (opcode 1) protected?** | Honda `jmcs` Type110: `HONDA_STATIC_CONFIRMED` that the single `AES_CTR_Update` runs *before* opcode dispatch, so opcode-1 bodies advance the same CTR state when screen security is on. Audi hook (Project B, pinned): `EXTERNAL_SOURCE_CONFIRMED` that its stream-111 receiver treats opcode 1 as `avcC config (NOT encrypted)` and decrypts only opcode 0. Modern xcertplay (pinned source, via `honda-vs-modern-type111-security.md`): clear VideoConfig; PlayPort's pinned source shares that lineage but its VideoConfig protection was not separately checked here. ClarityLink `Receiver`: accepts opcode 1 only for `CURRENT_IOS_TYPE111` and reads it clear; the legacy profile fails closed with `video_config_not_implemented`. | **Unresolved by design.** Honda Type110 and the external Type111 receivers disagree, and Honda Type111 is `UNKNOWN`. This corrects an implicit assumption in earlier ClarityLink wording: the clear-config path is correct for the *modern* profile only, and must not be presented as Honda-compatible. A legacy-AES Honda Type111 would need the opcode-1 policy (clear or inside the CTR stream) decided from a real session. Until then the legacy path stays fail-closed. See the [admission matrix](cl-honda-111-01-receiver-admission-matrix.md), row S6. |
| C3 | **Does Honda lack the modern capability tokens?** Honda's `jmcs` has no `extendedFeatures` / `altScreen` / `viewAreas` string literals. | `honda-info-capabilities.md`, `prior-art-altscreen.md` | The Audi stock `libairplay` 210.81 also has *no* `extendedFeatures` string, and Project B injects `["altScreen","viewAreas"]` into the `/info` dictionary. A missing token is therefore **not evidence that the receiver cannot carry Type111**, and equally not evidence that it can. Class: `EXTERNAL_SOURCE_CONFIRMED` for Audi, `HONDA_STATIC_CONFIRMED` for the absence. |
| C4 | **Is Honda Type111 skipped or rejected?** Early notes describe an "invalid-type path". | `honda-alt-screen-gating.md` (Step 29) vs `honda-stream-type-dispatch.md` / `honda-type111-rejection.md` (Step 38) | Step 38 supersedes Step 29: the default branch only logs, sets no status, removes no response and continues. Type111 alone yields an empty `streams` response when everything else succeeds. `HONDA_STATIC_CONFIRMED`. Phone behaviour on that response is `UNKNOWN`. |
| C5 | **What picks stream 110 versus 111 on the phone?** `type:111` in the display dictionary, or something else. | Project B source comment, citing the author's decompile of an iOS 26.6 sender | `EXTERNAL_AUTHOR_REPORTED`: the choice is a UUID comparison against display 0, plus the negotiated `altScreen` flag and a raw displays count of at least two. A second descriptor with a distinct identity is therefore necessary on that account but not shown sufficient. Honda's `uuid` field is numeric in the recovered builder, which the external receivers do not use. |
| C6 | **The 584×191 rectangle.** Appears in several ClarityLink docs as "the cast region". | `navigation-safe-area.md`, `hondahack-display-path.md` | It is HondaHack's *layout-local* ImageView size inside a 584×215 root with 24 px top padding. It is not an Android Display 1 coordinate, not an OEM Navigation rectangle and not a physical aperture. Nothing in this campaign uses it as a safe area. |
| C7 | **Project A's third-party URL list is stale.** The older prior-art note says the Audi/VW project URL was unavailable and used only MHI2. | `prior-art-altscreen.md` | Project B (`luka-dev/mib2q-carplay-rgi`) is now a fetched, pinned source. It is the first *shipping-production* stream-111 receiver in the project's evidence set. Its results (section 4, B rows) are source-level only. |
| C8 | **CL-AUTH-01 readiness wording on VideoConfig.** | `cl-auth-01-type111-readiness.md` row "VideoConfig": "whether real config frames are sealed is UNKNOWN" | Still correct, and now sharpened by C2: the Honda Type110 path seals them, Audi Type111 does not. PR #78 is unmerged and untouched. |

## 4. Evidence by topic

### 4.1 Honda receiver and Type110

| Fact | Class | Source |
|---|---|---|
| The receiver is an AirPlay-family native stack in `jmcs`, loaded by a service process; the Java layer is a thin AIDL wrapper. | `HONDA_STATIC_CONFIRMED` | CL-FACTORY-01 report 03 |
| `/info` is built by `AirPlayCopyServerInfo`, which asks the session for `displays`, receives a one-element array built from `ScreenCopyMain`, and the same dictionary is serialized to the phone. | `HONDA_STATIC_CONFIRMED` | `honda-server-info.md` (Step 32) |
| The descriptor fields are `edid`, `features`, `maxFPS`, `widthPhysical`, `heightPhysical`, `widthPixels`, `heightPixels` and a **numeric** `uuid`. `features` bit meanings are unknown. | `HONDA_STATIC_CONFIRMED` / `UNKNOWN` | `honda-display-capabilities.md` |
| `AirPlayReceiverSessionSetup` iterates `streams[]`; 100/101 audio, 110 screen; any other `type` (including 111) logs and continues without an error or response change. | `HONDA_STATIC_CONFIRMED` | `honda-stream-type-dispatch.md` |
| Type110 SETUP reads a nonzero uint64 `streamConnectionID`, derives key and IV with `AirPlay_DeriveAESKeySHA512ForScreen` from the 16-byte session master material, installs AES-CTR at the screen object, opens an ephemeral listener and returns `{type:110,dataPort}`. | `HONDA_STATIC_CONFIRMED` | `honda-screen-crypto.md`, `type111-security-contract.md` |
| Teardown iterates `streams[]`; 110 reaches `_ScreenTearDown`; type 111 receives no Honda cleanup. | `HONDA_STATIC_CONFIRMED` | `honda-mixed-stream-setup.md` |
| The proxy `libcarplay_proxy` registers one screen callback set behind a single global flag; a second registration returns "already registered". | `HONDA_STATIC_CONFIRMED` | CL-FACTORY-01 report 05 |
| Decoding is by Android MediaCodec fed by the receiver, not inside the proxy. | `HONDA_STATIC_CONFIRMED` | report 05 |
| No Android-service API hands out the authenticated session, master material, accepted socket or Setup bytes. | `HONDA_STATIC_CONFIRMED` (absence in the reviewed set) → `UNSUPPORTED` | `type111-security-access-matrix.md` |

### 4.2 Honda display host and HondaHack

| Fact | Class | Source |
|---|---|---|
| Honda's ExternalDisplay Out service observes an existing Android external display (the last enumerated); it does not create a virtual display. | `HONDA_STATIC_CONFIRMED` | CL-FACTORY-01 report 07 |
| It attaches three separate full-frame windows (bottom, main, interrupt), interrupt last. Interrupt visibility toggles independently; the main tree is preserved while an interrupt shows. | `HONDA_STATIC_CONFIRMED` | report 07, `43t1-r4d` |
| Display removal tears the stack down immediately; display return rebuilds only if the display is valid. | `HONDA_STATIC_CONFIRMED` | report 07 (G-03) |
| Factory cluster Navigation is structured turn-by-turn data rendered host-side into Android Views, not video. | `HONDA_STATIC_CONFIRMED` | report 06 |
| Display 1 captures are 800×480 in every state; SurfaceFlinger shows full-frame source and destination; the photographed cluster contains indicators absent from the capture. | `HONDA_PRIOR_RUNTIME` | `hondahack-display-path.md`, `navigation-safe-area.md` |
| The selectable cluster pages are addressed by a numeric display-contents identifier plus a status. The host requests a page with an interrupt notification and reports what it displays with a status notification; both travel through the ExternalDisplay AP service to a CPU-communication service that also carries B-CAN channel and cooperation messages. | `HONDA_STATIC_CONFIRMED` (call chain; vehicle-side effect `UNKNOWN`) | private; role-level in the [Navigation-pane contract](cl-honda-111-01-navigation-pane-contract.md) |
| HondaHack's view follows the host's reported (contents id, status): it asks for the interrupt-layout root first and uses it when visible, otherwise the main-layout root; visible only while one of two identifiers is active, hidden on a different active content, unchanged on status "none"; it claims the cluster by sending the host's own interrupt notification for a different-purpose slot. Stop Casting flips visibility and leaves the view attached. | `HONDAHACK_STATIC` (control flow from the preserved decompile; getter identities from the external decode, C1) | private |
| HondaHack casting: Display 0 screenshot at 400×240 ARGB_8888 → 384,000-byte `MemoryFile` → `Messenger` → bitmap → `ImageView` → view inserted with `addView(view, 0)` into the host's main layout. | `HONDAHACK_STATIC` | `hondahack-static-analysis.md` |
| HondaHack also hooks the host's navigation callbacks and calls an LVDS-interrupt notification to take visual priority. | `HONDAHACK_STATIC` (via the external decode, C1) | private `REPORT.md` |
| One recorded Door Open warning preempted and then restored casting. | `HONDA_PRIOR_RUNTIME` (single sample) | `test4c_preemption_model.py`, `cl-r10b` |
| HondaHack's insertion runs inside the Honda host process through Xposed. It is not a supported or permission-checked interface and has no declared caller identity. | `HONDAHACK_STATIC` | `cl-r10b-display-ownership.md` |
| The physical Navigation aperture, runtime view bounds, clipping, other warning classes, Navigation-page exit and re-entry, "Stop Casting" restoration and host-process loss with injected content are not established. | `UNKNOWN` | `navigation-safe-area.md`, `cl-hh-03` |

### 4.3 External references (source read in this campaign)

| Project | Finding | Class | Honda caveat |
|---|---|---|---|
| **B Audi MHI2Q** | Interposes the stock `/info` builder, adds `extendedFeatures ["altScreen","viewAreas"]` and a second display whose identity differs from the main display; its descriptor also needs `initialVideoStreams` (origin, uuid, zIndex) or the author reports the phone tears the session down. | `EXTERNAL_SOURCE_CONFIRMED` (code) / `EXTERNAL_AUTHOR_REPORTED` (phone reaction) | Honda `/info` field set and phone reaction are unknown. |
| | Calls the stock SETUP first, finds the `type==111` entry, reads `streamConnectionID`, derives key/IV with the stock `AirPlay_DeriveAESKeySHA512ForScreen` from the **session AES key** and that ID, opens its own listener on an adjacent preferred port, answers `{type:111,dataPort}`, and starts the acceptor before publishing the descriptor so a thread failure leaves no dead entry. | `EXTERNAL_SOURCE_CONFIRMED` | Offsets and session layout are QNX/210.81 specific. Honda has the same *named* derivation function, a strong lead and no proof. |
| | Receiver: 128-byte header, opcode 1 = unencrypted avcC config, opcode 0 = AES-CTR AVCC access unit, 2/4/5 ignored; bounded body size; stop flag polled so teardown unblocks the thread. | `EXTERNAL_SOURCE_CONFIRMED` | See C2. |
| | Per-stream TEARDOWN stops the 111 receiver only when the request contains type 111; session-level teardown always does; stale slots are reaped; pointer reuse on fast reconnect is handled by retiring older slots and a generation guard. | `EXTERNAL_SOURCE_CONFIRMED` | The bounded-slot, generation-guard and "teardown only for the owning stream" shape is portable as design. |
| | Rendering is a **separate external process** fed over a local wire; it owns the cluster surface. | `EXTERNAL_SOURCE_CONFIRMED` | On Honda the render host is an Android process the factory owns. |
| | Ships an installer that replaces firmware files and warns that only one mod may own the cluster. | `EXTERNAL_SOURCE_CONFIRMED` | A firmware-modifying installer is outside this campaign's authority. |
| **C Harman MHI2** | Same pattern on a different build: stock Setup first with the original request, clone the 111 descriptor for the response, own a separate listener/generation, treat transport and UI selection as separate. | `EXTERNAL_SOURCE_CONFIRMED` (earlier audit at `c2f811f1…`; pin has moved) | Re-audit is cheap but not decision-changing. |
| **D MIB2 High** | Separate stream for the cluster, with the instruction card adapting to the car's **VIEW-button layout changes**; separate HUD path; licence is per component. | `EXTERNAL_AUTHOR_REPORTED` | Confirms that cluster *page/layout selection* is a first-class input to a secondary renderer, matching the Navigation-page requirement here. |
| **I LIVI** | Authenticated-session ownership stays with the receiver; the recorded ClarityLink delegate patch no longer matches upstream. | see CL-AUTH-01 currency check | **Not a dependency.** The Honda hypothesis is a separate architecture. |
| **G PlayPort** | Pin `9a0882dd…` (`youcci/playport`). Type 111 is a constant beside 110; both route to one media handler and answer `{type, dataPort}`; media state is keyed by (session, type); the server's own config does not populate the cluster display by default, so it is an opt-in out-of-car oracle, not a Honda receiver. Prior ClarityLink lab observation of distinct 110 and 111 connection identities, VideoConfig and sustained frames in one historical session is `EXTERNAL_OBSERVATION`, not Honda evidence. | `EXTERNAL_SOURCE_CONFIRMED` | Its crypto family (HKDF, ChaCha20-Poly1305) is not Honda's Type110 scheme and must not be ported. |
| **H xcertplay** | Pins `3753867f…` and `17c92439…` (`shilapi/xcertplay`). Separate main and cluster display entries with UUIDs, `altScreen` added to enabled features only when a cluster is configured, stream dispatch on 110/111, clear VideoConfig, ChaCha20-Poly1305 frame bodies. | `EXTERNAL_SOURCE_CONFIRMED` | Standalone Android receiver; different authentication model. Classified by version: modern. |
| `alexpotv/Clusters` | Civic overlay on the last display plus private vendor display-control calls; no ownership lease; teardown not shown for abnormal exit. | `EXTERNAL_SOURCE_CONFIRMED` (per CL-R10B) | Different car, no licence, unsupported. |

### 4.4 ClarityLink code (synthetic)

| Component | Status |
|---|---|
| Host-side Type111 SETUP contract, once-only serializer, rollback, listener ownership | `SYNTHETIC_TESTED` |
| Per-generation stream identity, parent teardown, secondary teardown that leaves Type110 intact | `SYNTHETIC_TESTED` (jmcs `Receiver`, `PresentationStreamCoordinator`) |
| `FrameGate` bounded generation-gated queue | `SYNTHETIC_TESTED` |
| `SimulatedClusterHost` main plus interrupt layers, validity-gated rebuild | `SYNTHETIC_TESTED` |
| `FactoryIntegrationContract` and `HondaDisplay1OutputAdapter` | Fail closed; `safe_for_honda()` is hard `False` |
| API17 structured-navigation renderer and lifecycle (PR #77) | API17 runtime evidence for *structured* content only; **not** Honda admission |
| CL-AUTH-01 trust classes, security grants, parent revocation (PR #78) | Open, unmerged, not consumed by code in this campaign |

### 4.5 Tooling note (Project J)

REA, JADX and Ghidra are present in the lawful local toolchain. This campaign used the **existing** JADX and baksmali outputs (Honda services deodexed under CL-FACTORY-01; HondaHack decompiled under the HondaHack-Research tree) with targeted grep and read of specific classes, plus `strings` on the preserved HondaHack DEX to test the encrypted-constant claim. No new REA evidence IDs were created and no unverified analysis binary was downloaded or run. Findings that depend on private decompiled output are therefore recorded as role-level conclusions here and as line-referenced notes in private storage, not as REA-linked evidence.

## 5. What the map shows

1. The Honda receiver's missing Type111 behaviour is narrow and precisely located: a skipped branch in SETUP, a one-descriptor `/info` builder, a singleton proxy registration and a Type110-only teardown. Everything else needed by a receiver-owned child stream (an authenticated parent, a same-named screen KDF, an ephemeral-listener pattern) exists inside the factory process and nowhere outside it.
2. No reviewed Honda interface lets any other process obtain the parent session, master material, accepted socket or the Setup transaction. The only candidate extension points are inside `jmcs`, and entering them means interposing factory code, which this campaign does not authorize.
3. The display side has a demonstrated private technical path (HondaHack) and a statically understood host (separate main and interrupt windows), but no supported caller contract, no physical aperture, and no runtime evidence about the Navigation page selection.
4. The two critical gates are therefore both **evidence- and authorization-limited, not code-limited**.
