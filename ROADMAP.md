# ClarityLink roadmap

## R6A architecture pivot — 2026-10-04

**PRIMARY ARCHITECTURE:** clean-room Honda-compatible custom CarPlay receiver owning Type110 and Type111 in one session. **STOCK jmcs INTERPOSITION:** parked under R3C. **DESCENDANT FIRMWARE RESEARCH:** opportunistic supporting research. **IMMEDIATE TARGET:** real iPhone Type111 negotiation, security, media, decode and host display (R6-L7). **HONDA DEPLOYMENT:** not authorized. The [R6A ADR](research/adr/r6-custom-receiver-primary-architecture.md), [readiness matrix](research/runtime/r6a-custom-receiver-readiness.md), and [milestone report](step-reports/43t1-r6a-custom-receiver-canonical-pivot.md) supersede the R5D next-action recommendation. Current Python receiver reaches host synthetic T1 only; MFi/auth, full /info, real Type111 framing/security and Honda adapters remain open.


**Goal:** preserve stock Honda CarPlay on the center display while providing useful, independently sourced navigation content in the instrument cluster's Navigation region. The source must be user controlled and legally available; the current host model uses synthetic steps. Preserve all other stock safety and cluster UI.

## Current engineering stage

[R5D artifact provenance closure](step-reports/43t1-r5d-artifact-provenance-closure.md) is the latest canonical research milestone: `R5D_HIGH_CONFIDENCE_PACKAGE_LEAD_FOUND` / `GO_FOR_MORE_PUBLIC_ARTIFACT_RESEARCH`. A reproduced EU Civic bulletin names MELCO MRC12.4, `1.F197.70` and `MRC_EU_SW_v12_4.zip`, but original PANEX access is gated and an available mirror lacks authenticated custody. The official US Civic `1.F197.60`/`1.F196.39` pair remains VIN/dealer selected. No lawful analyzable descendant receiver payload or Type111 triage resulted. Next research should seek original publisher hash/custody or a different publicly hosted package. R3C runtime `jmcs`/Type111 NO-GO controls; R4D Display 1 remains possible but unproven; R5X/R5Y and separate R5Z remain host-only models. Rules v2 governs and only offline/public research is authorized.

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

## Workstream and gates

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

## Invariants

- Stock Type110 response, data path, crypto state, center display, and audio remain unchanged.
- Type111-only failure must clean up Type111-owned resources only.
- Synthetic and external-prior-art fields retain their evidence labels.
- Live Type111 and jmcs no-op loading remain NOT READY until their explicit gates pass.


## R5B — Honda descendant artifact search (2026-10-04)

R5B found versioned public research metadata for a close 2016–2021 Civic Andromeda/vcm30t30 family, including a 2021 Civic EX `1.F1A5.15` lead. No lawful, versioned descendant receiver payload was available for review, so Type111 remains `TYPE111_INSUFFICIENT_ARTIFACT`; this does not establish absence. The next milestone is continued public artifact/provenance research. R3C runtime NO-GO remains, R5X remains MODEL_ONLY, R4D Display 1 remains possible but unproven, and no vehicle action is authorized. See [R5B report](step-reports/43t1-r5b-honda-descendant-artifact-and-type111-static-triage.md).
