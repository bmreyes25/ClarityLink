# ClarityLink roadmap

**Goal:** preserve stock Honda CarPlay on the center display while providing useful, independently sourced navigation content in the instrument cluster's Navigation region. The source must be user controlled and legally available; the current host model uses synthetic steps. Preserve all other stock safety and cluster UI.

## Current engineering stage

The latest completed public research milestone is [R5B public artifact research](step-reports/43t1-r5b-honda-descendant-artifact-and-type111-static-triage.md): `R5B_NO_LAWFUL_ANALYZABLE_ARTIFACT_FOUND` / `GO_FOR_MORE_PUBLIC_ARTIFACT_RESEARCH`. The 2021 Civic EX `1.F1A5.15` metadata is the strongest related lead; no lawful analyzable receiver payload has been found. R3C's `jmcs`/Type111 runtime NO-GO remains controlling, R4D ordinary-app Display 1 remains possible but unproven, and [R5X](step-reports/43t1-r5x-theoretical-jmcs-type111-patch-sandbox.md) remains a host-only model. Rules v2 governs. Only offline/public research is authorized.

A separate [R5Y host-only receiver-core sandbox](step-reports/43t1-r5y-reusable-type111-receiver-core-sandbox.md) completed at `a88d679` during R5C inventory. It is a model, not Honda integration, and does not change the current evidence gate.

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
