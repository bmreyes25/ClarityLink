# ClarityLink primary goal — genuine secondary CarPlay (Type111)

> **PRIMARY GOAL: iPhone-origin Type111 secondary CarPlay video on factory Display 1, simultaneous with normal Type110 on Display 0.**

This is the canonical, owner-stated objective (clarified 2026-10-23). It takes precedence over any ambiguous architecture description, lab name or synthetic demonstration in this repository. If another document reads as if the goal were a custom navigation interface, this document wins.

`safeForHonda()` remains `false`. `VEHICLE_DEPLOYMENT_NOT_AUTHORIZED`. CL-POLICY-02 / PR [#91](https://github.com/bmreyes25/ClarityLink/pull/91) merged in `origin/main` at `1cc3e63541074f9c2324c91aeb4cff854ba7acde`; its authorization applies to offline research and prototypes under `docs/safety/vehicle-testing.md` only. The policy allows no vehicle work; nothing here authorizes installation, Honda ADB, firmware writes, vehicle testing, or connected-iPhone work. PRs [#92](https://github.com/bmreyes25/ClarityLink/pull/92), [#94](https://github.com/bmreyes25/ClarityLink/pull/94), and [#97](https://github.com/bmreyes25/ClarityLink/pull/97) are merged and provide synthetic lifecycle/ingestion and fail-closed error-handling evidence only. Current vehicle status remains `VEHICLE_DEPLOYMENT_NOT_AUTHORIZED`.

## Required architecture

| Element | Requirement |
|---|---|
| Display 0 | Existing factory CarPlay: apps, audio, calls, Siri. Unchanged and independent. |
| Display 1 | Secondary CarPlay content **provided by the connected iPhone through Type111**. |
| Receiver | Negotiates and maintains both streams without breaking the Type110 session. |
| Decoder | Decodes genuine Type111 video using the established protocol and an authorized security context. |
| Display adapter | Presents those decoded frames in the factory cluster's Navigation region. |
| Disconnect | Removes all custom content and restores factory-only display behavior. |
| Warnings | Factory warning and safety displays keep authority. |

What appears on Display 1 depends on what iOS and the app deliver through the supported session. A full second home screen or any particular third-party app output is **not** promised.

## Explicitly NOT the goal

None of these may be substituted for Type111, or reported as progress toward it:

- a homemade navigation interface, a custom map renderer, or a route drawn from GPS coordinates;
- a turn-by-turn-only widget (maneuver/distance/road-name cards);
- a modified Honda Navigation APK acting as a new maps app;
- mirroring Display 0 and calling it secondary CarPlay;
- replaying prerecorded video and claiming live CarPlay;
- simulated navigation frames presented as Type111 reception.

Synthetic video and mock navigation are allowed **only** in isolated laboratory tests that are labeled synthetic.

## Evidence categories (never interchangeable)

Every milestone, test and report must say which of these it validates. A result in one category says nothing about another.

| Category | Meaning |
|---|---|
| **Synthetic lifecycle** | Session, generation, lease, teardown and recovery behavior of ClarityLink's own models or API17 lab, on synthetic inputs. |
| **Type111 protocol handling** | Code that parses/builds real Type111 SETUP, framing, protection or VideoConfig, and how well it is validated (spec/prior-art, hand-built fixture, or capture). |
| **iPhone-origin video** | Frames that actually came from a real iPhone's secondary CarPlay stream, handled by ClarityLink code. A third-party receiver seeing frames is `OBSERVED-3P`, not this. |
| **Honda receiver integration** | ClarityLink negotiating and maintaining Type111 inside the factory receiver alongside Type110. |
| **Physical Display 1 output** | Pixels from that stream on the real cluster, with page ownership and warning priority respected. |

Cell vocabulary used below: `LAB` (proven in synthetic/API17 lab), `MODEL` (model only, never run on real data), `OBSERVED-3P` (seen in saved third-party-receiver evidence; no Honda, not by ClarityLink code), `STATIC` (statically identified in Honda artifacts), `PARTIAL`, `UNVERIFIED`, `MISSING` (no established contract or implementation), `N/A`.

Reporting rules: do not write bare "PASS" or "works"; name the category. Synthetic frames must be labeled synthetic wherever shown. The Honda and Physical columns may not use `LAB` or `OBSERVED-3P`.

## Ten-stage traceability matrix

Every stage below is **UNVERIFIED end to end**. No stage has been shown on a Honda. No stage has been shown with iPhone-origin bytes passing through ClarityLink code; the iPhone-origin column for stages 1–6 is third-party (PlayPort) observation only.

| # | Stage | Synthetic lifecycle | Type111 protocol handling | iPhone-origin video | Honda receiver integration | Physical Display 1 output |
|---|---|---|---|---|---|---|
| 1 | iPhone connects; normal Type110 CarPlay operates | LAB | STATIC | OBSERVED-3P | UNVERIFIED | N/A |
| 2 | Receiver advertises a genuine additional CarPlay display capability | LAB | PARTIAL | OBSERVED-3P | MISSING | N/A |
| 3 | iPhone negotiates the secondary stream | LAB | PARTIAL | OBSERVED-3P | MISSING | N/A |
| 4 | Type111 SETUP succeeds | LAB | PARTIAL | OBSERVED-3P | MISSING | N/A |
| 5 | Correct protected secondary video transport is established | MODEL | PARTIAL | OBSERVED-3P | MISSING | N/A |
| 6 | Genuine iPhone-origin Type111 frames are received | N/A | PARTIAL | OBSERVED-3P | MISSING | N/A |
| 7 | Frames are decoded and delivered to Display 1 | LAB | PARTIAL | UNVERIFIED | MISSING | UNVERIFIED |
| 8 | Display 0 keeps operating independently | LAB | N/A | OBSERVED-3P | UNVERIFIED | UNVERIFIED |
| 9 | Factory page ownership and warning priority respected | MODEL | N/A | N/A | MISSING | UNVERIFIED |
| 10 | Disconnect ends the secondary stream and restores factory-only | MODEL | N/A | UNVERIFIED | MISSING | UNVERIFIED |

Basis for the cells (audit findings plus merged synthetic work through `origin/main` at `1cc3e63541074f9c2324c91aeb4cff854ba7acde`; see the evidence-class limits below):

- **`OBSERVED-3P`** is the sanitized 43P PlayPort session (`research/lab/current-ios-type111-observation.md`, `research/lab/captures/43p/`): a real iPhone and a third-party receiver (identity details omitted), Type111 SETUP, VideoConfig and sustained frames on both streams. Transport protection is inferred from the third-party parser's active branch; no unprotect result was retained. It is event summaries only (no raw bytes, no media), the iPhone model/iOS build were not retained, and it is not Honda evidence. For stage 8 it shows only that Type111 video was delivered while Type110 stayed active; Type110 audio and independent teardown were not tested.
- **`PARTIAL` protocol handling** is the host-lab receiver (`src/claritylink-jmcs/claritylink_jmcs/`: `media.py` framing, `decoder.py` avcC/Annex-B and ffmpeg decode, `receiver.py` SETUP and `receive_secondary_frame`, `security.py` ChaCha parameters). Its fixtures are hand-built or locally generated; it has never processed iPhone-origin bytes (so stage 6 is `PARTIAL`: the receive path exists, no real bytes have gone through it), and the key is injected by the caller.
- **`MISSING` Honda receiver** means no supported Type111 SETUP fields, security context, data-port ownership or teardown contract is established for the Honda receiver (see `docs/status/integration-readiness.md`, `research/carplay/type111-unknown-register.md`).
- **Stage 8:** Type110 continuity is `LAB`-proven for the synthetic lifecycle only; independence under a real iPhone stream on a Honda is unverified.
- **Stages 9–10** rest on synthetic models: `SimulatedClusterHost`, API17 pane leases, and the merged lease-fence/fail-safe work from PR #92 (synthetic; it does not prove Honda behavior).

## What is real Type111 pipeline and what is not

| Class | Components (representative) | Status |
|---|---|---|
| **Type111 protocol handling** (host lab) | `claritylink_jmcs` `media.py`, `decoder.py`, `receiver.py`, `security.py`, `setup.py`, `info.py` | Real wire-format code paths; spec/prior-art and hand-built fixtures only; never run on iPhone-origin bytes; key injected. |
| **Type110, Honda-derived** | `claritylink-transport` `screen_parser.py`, `h264_extractor.py`, `video_config.py`, `crypto_model.py`; `claritylink-negotiation/screen_kdf.py` | From Honda static analysis. Whether Type111 uses the same framing/KDF is `HONDA_UNKNOWN`. |
| **Authentication / security entry** | `mfi_oracle.py`, `authentication.py`, `auth.py`, `auth_providers/*`, `honda_substrate.py` | Synthetic, replay, or fail-closed stubs. No real phone authentication; Honda factory authentication absent (`EVIDENCE_REQUIRED`). Bench bridge code for user-owned hardware (`tools/r6h_livi_receiver.py`) has no recorded real run. |
| **Content-agnostic frame plumbing** | `FrameGate`, `PerStreamFrameDispatcher`, `ClarityLinkRenderer`, API17 `Display1OutputBackend`/`PaneLease`/`FrameDispatchGate`, `SimulatedClusterHost`, decoders `Api17*H264Decoder` | Do not inspect content; renderer accepts decoded RGBA frames only. Bound to simulated hosts; `honda_output.py` always fails closed because no Honda frame-admission contract is known. |
| **Synthetic lifecycle models** | `synthetic_type111_replay`, `legacy_dual_screen_twin`, `carplay-session-model/*`, interposer/negotiation models, `Type111ControlPlane`/`Type111ProducerService` (Android lab IPC) | Model only. Names containing "Type111" in the Android lab do **not** speak the CarPlay control protocol. |
| **Fail-safe** | Lease fence and coordinator, merged PR #92 | Synthetic lifecycle only. Content-agnostic by design: it takes opaque content and has no protocol knowledge. |
| **Type111 ingest** | Offline ingest pipeline, merged PR #94; fail-closed error-handling hardening, merged PR #97 | Offline/synthetic only; no iPhone-origin frames or Honda integration established. |

### Navigation-UI drift (separate lab track — "NAV-LAB")

Not on the Type111 video path, and **not progress toward the primary goal**: `cluster_navigation_model.py`, `synthetic_navigation_pipeline.py`, `turn_cards.py`, `cl_factory_02_demo.py`, the PR #77 structured-navigation path (`NavigationUpdate`, `StructuredNavigation*` in the API17 renderer, `StructuredNavigationLabActivity`, `tools/build_cl_factory_03_api17_apk.sh`) and their tests. It models semantic maneuver/distance/road-name updates, deliberately "not a decoded Type111 video frame". It reuses generic plumbing (`FrameGate`, simulated host) and sits beside the Type111 classes, which is how it can be mistaken for the real path. Rules:

- Do not extend NAV-LAB to advance the goal, and do not report NAV-LAB results under any Type111 category.
- Its docstrings are historical and honest ("NOT a decoded Type111 video frame") and are left unmodified so this change stays documentation-only; this document is the authority on how to read them. A later source change may add a one-line "NAV-LAB, not Type111 video" banner to each.
- Keep the useful generic safety ideas it contributed (generation fencing, warning withdrawal, restore) only through the content-agnostic components above.

## Interfaces still required for API17 and target integration

Merged PRs #92 and #97 connect the host-lab Type111 receiver to the synthetic lease-gated fail-safe. That offline Python path is not an Android/MediaCodec integration or a Honda-supported path. The following production/API17 or OEM boundaries remain incomplete:

1. **Authenticated session and stream ownership** — a real security-context provider that derives the Type111 protection key from a legitimately authenticated session (today the key is injected, the authority synthetic or absent).
2. **Receiver → decoder bridge** — Type111 socket → framing → unprotect → avcC → Android MediaCodec decoders. The Python parser is host-only; the Android/native side has only synthetic lab framing.
3. **API17 frame type and decoder integration** — the host-lab path has an immutable RGB24 `VideoFrame`; the Android MediaCodec/output path still has separate frame representations and no Type111 receiver-to-decoder integration.
4. **API17 display adapter and autonomous withdrawal** — the Python `LeaseGatedOutput` submits lease-bound frames to the simulated host. The API17 renderer is not connected to the Type111 receiver/fence, and it still needs host-owned expiry/withdrawal without producer `tick()` (CL-INT-04).
5. **API17 fault mapping and resource ownership** — Python host-lab fault mapping and cleanup exist; Android receiver/decoder process faults, listeners, security teardown, and display-host cleanup are not wired into a production API17 integration.
6. **Host-side fence** on the actual display host, evaluated on every composition and from a timer (today Python, lazy, branch-only).
7. **Honda contracts** — receiver admission/ownership/revocation, and a display frame-admission/geometry/page/warning/restore contract. Both `MISSING`; not to be invented.

## Milestone → category map

"Validates" lists only what the milestone actually supports. Blank means it does not.

| Milestone / PR | Synthetic lifecycle | Type111 protocol handling | iPhone-origin video | Honda receiver integration | Physical Display 1 output |
|---|---|---|---|---|---|
| CL-R4, CL-R7 (API17 lab) | yes | model only | no | no | no |
| CL-R6 host-lab receiver (`claritylink_jmcs`) | yes | yes, hand-built fixtures | no | no | no |
| 43P PlayPort observation | no | prior-art for the above | observed by a third-party receiver | no | no |
| CL-R9/R10/CL-IF-02A (PRs #47–49, #88) | no | static Honda Type110; Type111 unsupported in reviewed paths | no | static only | no |
| CL-HH-02 / CL-DISP-02 (#87) | no | no | no | no | static Honda display ownership only |
| CL-FACTORY-01/02, PR #77 (NAV-LAB) | navigation-state lifecycle only | **no** | **no** | no | no |
| CL-OBS-02 / CL-OFFLINE-GATE-01 (#89, #90) | no | no | no | planning of read-only evidence only | no |
| CL-INT-03 fail-safe (#92, merged) | yes | no | no | no | no |
| CL-T111-INGEST-01 / fail-closed ingest (#97, merged) | yes | synthetic/prior-art fixtures | no | no | no |

## Next engineering milestone

**CL-INT-04 — autonomous host-owned Display 1 withdrawal (offline/API17).** Reuse the merged fail-safe, Type111 ingest, and error-handling infrastructure from PRs #92, #94, and #97. Implement and verify host-owned timer/lease expiry that withdraws Display 1 without producer `tick()`, producer-process death handling, stale-generation fencing, Type110 independence, safe host restart and teardown, and accurate cleanup-failure reporting. Require actual Android API 17 emulator runtime verification of the withdrawal and recovery paths. Keep all inputs synthetic and the implementation fail-closed. This validates **Synthetic lifecycle** only; it does not validate iPhone-origin video, Honda receiver integration, or physical Display 1 output. No Honda, ADB, vehicle, or connected-iPhone operation is in scope; `safeForHonda()` remains `false`.

It is paired with an **owner-gated** item that is the true critical path and cannot be done offline: obtaining sanitized byte-level Type111 fixtures from a real iPhone through an authorized bench receiver (CL-REC-01), then replaying them through the same code. That requires separate explicit owner authorization and a legitimately authenticated session; no live iPhone use, authentication bypass or secret extraction is authorized here. It involves no Honda connection, and the public repository would receive only sanitized fixtures after a separate public-safety review.

## Follow-up for pinned governance files

`AGENTS.md`, `README.md` and `docs/README.md` are digest-pinned in repository health scope. PR #91 refreshed the changed pinned hashes in its policy scope. Preserve those hashes in future edits and use the PRIMARY GOAL sentence above when updating governance pointers. README wording now describes offline Type111 research and keeps vehicle deployment separately unauthorized.
