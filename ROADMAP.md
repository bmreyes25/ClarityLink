# ClarityLink roadmap

## R7 offline implementation first — 2026-10-06

**`R7_OFFLINE_IMPLEMENTATION_FIRST`** supersedes the R6 CPC200 prerequisite for offline receiver development. R7A starts from verified main `c254d7f6172dbd45bb1cd6a87b10bcb4cd96d811` and builds on existing R6 receiver/session/security components. R7A outcome: `R7A_INTEGRATED_SYNTHETIC_DUAL_STREAM_PASS`, host/model-only. The 901-pass repository suite and local repository health passed; exact pushed-head Offline CI and CodeQL are pending PR execution. See [R7A report](step-reports/43t1-r7a-integrated-offline-dual-carplay.md) and [adapter boundary inventory](research/runtime/r7a-host-honda-boundary-inventory.md).

Next: **`GO_FOR_R7B_ANDROID_API17_ARMV7_NATIVE_BUILD`**. CPC200 remains optional for R7B. Genuine MFi, real iPhone negotiation, real Type111 security/media, Honda auth/USB ownership, target executable compatibility, Display1 admission, safety coexistence and stock restoration remain unresolved. No R7A result promotes R6 evidence or authorizes Honda/vehicle action.

The R6 chronology below remains historical evidence, not deleted or retrospectively rewritten. Its CPC200-gated real-session path remains relevant to later real-iPhone validation.

## Canonical seven-gate program — 2026-10-05

1. **Gate 1 — Mac auth/control authority:** R6H is blocked on completing the LIVI Node IPC/authentication proof and app-root wiring; CPC200 is absent.
2. **Gate 2 — Complete Mac receiver:** not started; real `/info`, SETUP and Type110/111 follow Gate 1.
3. **Gate 3 — API17/ARMv7 build:** not started.
4. **Gate 4 — Honda process/lifecycle:** not started; no Honda work authorized in this milestone.
5. **Gate 5 — Honda Display1:** not started.
6. **Gate 6 — Honda Display0:** not started.
7. **Gate 7 — Honda USB/iAP2/auth architecture:** not started.

R6H result: `GATE1_SOFTWARE_READY_HARDWARE_REQUIRED`; next `GO_FOR_GATE1_HARDWARE_AUTHORITY_BRINGUP`. No Gate 2 work begins until the real Gate 1 criterion is met.

## Canonical Mac receiver trajectory

**R6F authority selection** → **R6G LIVI seam** → **R6H Gate 1 software bridge + genuine Mac authority bring-up** → **Gate 1 real authenticated control session and /info+SETUP ownership** → **Gate 2 complete Mac receiver** → **Gate 3 API17/ARMv7 build** → **Gate 4 Honda process/lifecycle** → **Gate 5 Honda Display1** → **Gate 6 Honda Display0** → **Gate 7 Honda USB/iAP2/auth architecture**. Honda stages remain later; no Honda work is authorized by R6H. R6F did not contact Honda, use ADB, or connect to a vehicle. Synthetic/replay evidence cannot satisfy these real-iPhone gates. See [R6F authority acquisition](research/runtime/r6f-authority-acquisition-specification.md) and [complete Mac receiver roadmap](research/runtime/r6f-complete-mac-receiver-roadmap.md).

## R6G authority/control handoff result — 2026-10-05

R6F PR #11 merged at `7fadb23b2fa599a82207ae22a2f1fc2e1a6757ee`. R6G public source review found LIVI's `CpStack.attachSocket` owns parsing, dispatch, and the sole response writer; the narrow seam is before `_handle`, requiring a small upstream delegate patch. The Python ClarityLink provider is implemented to the existing boundary, but the LIVI delegate/bridge is not; adapter result `R6G_LIVI_ADAPTER_PARTIAL`. CPC200 not detected, no provisioning or real iPhone attempt; highest tier `BELOW_R6G_T0`. Next is `GO_FOR_R6H_LIVI_ADAPTER_COMPLETION`, then hardware bring-up and real `/info`. See [R6G report](step-reports/43t1-r6g-livi-authority-bringup.md) and [seam](research/runtime/r6g-livi-control-session-seam.md). No Honda work.


## R6F authority selection and R6G action

R6E merged at `9ab9d77`. R6F selected user-owned Carlinkit CPC200-CCPA + LIVI Link/LIVI macOS receiver as the concrete acquisition path; no unit is present, no ClarityLink control handoff exists, and no real iPhone gate was reached. **R6G:** acquire and verify the exact hardware revision, establish genuine authority, adapt the LIVI authenticated control session, then drive real `/info`, SETUP and Type111. See [R6F acquisition](research/runtime/r6f-authority-acquisition-specification.md) and [R6F report](step-reports/43t1-r6f-authority-integration.md). Honda deployment remains later and separate.

## R6D factory handoff decision

R6D closes the reviewed factory external-handoff path: iAP2 auth and AirPlay receiver are process-local within `jmcs`, with no supported transfer API found. [Decision matrix](research/runtime/r6d-factory-auth-handoff-decision-matrix.md). **R6E:** integrate an authorized host MFi hardware/service and authenticated CarPlay control transport into the custom receiver, then attempt real iPhone `/info` and Setup on Mac. Honda deployment remains a later, separately reviewed milestone. The R6C `ARCH_UNKNOWN` label is historical; R6D makes a bounded interface decision without assigning a new meaning to informal ARCH labels.

## R6C substrate result

R6C traced factory USB/iAP2/MFi and AirPlay ownership inside preserved `jmcs`, including a configured I²C authentication channel. The desired factory authenticated-session handoff remains unresolved. R6D should close the internal auth/iAP2→AirPlay edge and search for a supported boundary before any live observation or target adapter binding. [R6C report](step-reports/43t1-r6c-honda-auth-substrate-reuse.md). The custom receiver remains primary; stock `jmcs` interposition remains parked under R3C.


## R6B authentication boundary — 2026-10-04

**PRIMARY ARCHITECTURE:** custom Honda-compatible receiver. PR #4 merged at `07f7316`; R6B starts from that main commit. **AUTH RESULT:** adapter/replay interfaces complete, no authorized hardware/service or authenticated control handoff connected. **REAL IPHONE:** not reached by ClarityLink. **HIGHEST LEVEL:** R6-L1; R6B below T0. **NEXT:** integrate a user-owned genuine MFi coprocessor or licensed service and its control-session handoff, then attempt real `/info` and SETUP on Mac. **HONDA DEPLOYMENT:** not authorized. See the [R6B report](step-reports/43t1-r6b-authentication-and-real-ios-negotiation.md), [readiness](research/runtime/r6b-custom-receiver-readiness.md), and [auth inventory](research/runtime/r6b-authentication-session-inventory.md).


## Historical R6A architecture pivot — 2026-10-04

**PRIMARY ARCHITECTURE:** clean-room Honda-compatible custom CarPlay receiver owning Type110 and Type111 in one session. **STOCK jmcs INTERPOSITION:** parked under R3C. **DESCENDANT FIRMWARE RESEARCH:** opportunistic supporting research. **IMMEDIATE TARGET:** real iPhone Type111 negotiation, security, media, decode and host display (R6-L7). **HONDA DEPLOYMENT:** not authorized. The [R6A ADR](research/adr/r6-custom-receiver-primary-architecture.md), [readiness matrix](research/runtime/r6a-custom-receiver-readiness.md), and [milestone report](step-reports/43t1-r6a-custom-receiver-canonical-pivot.md) supersede the R5D next-action recommendation. Current Python receiver reaches host synthetic T1 only; MFi/auth, full /info, real Type111 framing/security and Honda adapters remain open.


**Goal:** one simultaneous iPhone CarPlay session, normal Type110 center display, and independent Type111 navigation video on the cluster, with stock-quality audio, controls, warning coexistence and teardown.

## R6A engineering stage (historical)

R6A merged R5Z onto R5D main and selected the custom receiver as primary. The Python host reference passes synthetic T1; no real iPhone Setup/media has reached it. R6B starts with legitimate host authentication/session ownership and full `/info`. Honda USB/iAP2/MFi/audio/control/display/lifecycle adapters remain evidence gated. Descendant firmware is opportunistic.

| Level | Gate | Status |
|---|---|---|
| R6-L0 | architecture pivot | complete |
| R6-L1 | integrated receiver core | complete on host |
| R6-L2 | full host /info + authenticated Setup | open |
| R6-L3 | real Type111 listener connection | open |
| R6-L4 | real Type111 framing | open |
| R6-L5 | real Type111 security | open |
| R6-L6 | decoded real Type111 frame | open |
| R6-L7 | displayed real Type111 host window | immediate target |
| R6-L8 | complete host Type110+Type111 receiver | future |
| R6-L9 | API17/ARMv7 build | future |
| R6-L10 | Honda substrate adapters | future |
| R6-L11 | separately authorized parked-car execution | not authorized |
| R6-L12 | simultaneous in-car displays | final target |

## Historical roadmap and stock receiver research

## Historical receiver target (superseded by R3C/R4A)

The target architecture keeps Honda Type110 stock and adds a separate Type111 path inside/alongside the CarPlay session owner, with a renderer adapter in the ExternalDisplay host. Those integration seams remain unproven for Honda.

```mermaid
flowchart LR
  Phone[iPhone session] --> jmcs[Honda jmcs]
  jmcs -->|stock Type110| Center[Center CarPlay]
  jmcs -.->|proposed, unresolved| Type111[ClarityLink Type111]
  Type111 -.-> Receiver[ScreenStream / H.264]
  Receiver -.-> Render[ExternalDisplay renderer adapter]
  Render -.-> Cluster[Cluster Navigation region]
```

## Historical workstream and gates

| Workstream | Current state | Next gate |
|---|---|---|
| Offline digital twin | Synthetic visual and transaction models are available | Models remain distinct from Honda proof |
| Honda `/info` / Type111 | Stock Type110 path has static evidence; Honda Type111 acceptance/schema unknown | Preserve as unknown until specifically evidenced |
| Type111 security/session | Type110 evidence does not prove Type111 crypto or lifecycle | No crypto selection or negotiation authorization |
| Honda network preflight | D0-3 read-only procedure reviewed; earlier attempt stopped before target reads | Separately initiated D4 observation under current gates |
| `jmcs` integration | Expanded R3C found no safe additive runtime extension path in preserved evidence | Pivot offline; reopen only on new static evidence |
| Cluster rendering | Host-side mock exists; real Display Audio frame handoff unresolved | Requires independent evidence and review |
| Vehicle deployment | Not implemented or authorized | Requires separately scoped, reviewed milestones |

## Important distinction

Apple, xcertplay, MHI2, and CPC200 establish external architecture or receiver-specific prior art. They do not prove Honda behavior. See the [source-pinned research](docs/research/carplay-altscreen-prior-art.md), [Honda research plan](docs/research/honda-type111-research-plan.md), [project state](PROJECT_STATE.md), and [next action](NEXT_ACTION.md).

## Historical stock-interposition invariants

- Stock Type110 response, data path, crypto state, center display, and audio remain unchanged.
- Type111-only failure must clean up Type111-owned resources only.
- Synthetic and external-prior-art fields retain their evidence labels.
- Live Type111 and jmcs no-op loading remain NOT READY until their explicit gates pass.


## R5B — Honda descendant artifact search (2026-10-04)

R5B found versioned public research metadata for a close 2016–2021 Civic Andromeda/vcm30t30 family, including a 2021 Civic EX `1.F1A5.15` lead. No lawful, versioned descendant receiver payload was available for review, so Type111 remains `TYPE111_INSUFFICIENT_ARTIFACT`; this does not establish absence. The next milestone is continued public artifact/provenance research. R3C runtime NO-GO remains, R5X remains MODEL_ONLY, R4D Display 1 remains possible but unproven, and no vehicle action is authorized. See [R5B report](step-reports/43t1-r5b-honda-descendant-artifact-and-type111-static-triage.md).

## R6 Gate trajectory (canonical)

R6F authority selection → R6G LIVI seam → R6H software delegate/bridge → **R6H1 CPC200/LIVI Link authority bring-up (Gate 1; blocked waiting for CPC200; Gate 1 remains open)** → real authenticated ClarityLink `/info` → Gate 2 complete real Mac receiver → Gate 3 API17/ARMv7 target build → Gate 4 Honda process/lifecycle adapter → Gate 5 Honda Display1 adapter → Gate 6 Honda Display0 adapter → Gate 7 Honda USB/iAP2/auth target architecture. Gate 2 remains `NOT_STARTED`; no Honda activity is authorized by this sequence. R6H1 reached no real-iPhone tier.
