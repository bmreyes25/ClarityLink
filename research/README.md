# Research archive

`research/` is ClarityLink's deep technical archive, not the recommended first entry point. Begin with the [project README](../README.md), [architecture overview](../docs/architecture/overview.md), and [evidence classification](../docs/development/evidence-classification.md). Check the claim-level [evidence index](../EVIDENCE_INDEX.md) before relying on a result.

## Browse by domain

| Domain | Areas | Curated starting points |
|---|---|---|
| CarPlay protocol | `carplay/`, `lab/` | [Honda capabilities](carplay/honda-info-capabilities.md), [Type111 unknown register](carplay/type111-unknown-register.md), [current-iOS observation](lab/current-ios-type111-observation.md) |
| Honda platform and runtime | `runtime/`, `deployment/`, `hondahack/`, `platform/` | [D0-3 network runbook](runtime/43t0d-live-runbook.md), [Honda runtime status](platform/honda-live-runtime.md), [Honda Type111 research plan](../docs/research/honda-type111-research-plan.md), [HondaHack display path](../step-reports/05c-hondahack-display-path.md) |
| Cluster and display | `display/`, renderer work in `src/` | [Display Audio host flow](display/externaldisplay-host-flow.md), [renderer model](../src/claritylink-renderer/README.md), [visual cluster twin report](../step-reports/42k-actual-decoded-frame-visual-demo.md) |
| Architecture and contracts | `architecture/`, `adr/`, `plans/` | [active Type111 architecture](architecture/type111-active-architecture.md), [Type110 invariants](architecture/type110-invariants.md), [decision index](adr/README.md) |
| Evidence and inventory | `evidence/`, `inventory/`, `acquisition/` | [second-display evidence ledger](evidence/second-display-ledger.md), [historical acquisition recovery guide (superseded)](acquisition/TERMINAL_RESUME_GUIDE.md) |
| Simulator and digital twin | `simulator/`, `local-model/` | [simulator notes](simulator/), [offline visual demo](../demo/type111/README.md) |
| Native and deployment research | `native/`, `verification/`, `deployment/` | [PREP2 restoration verifier](runtime/43t1-restoration-verifier.md), [PREP2 offline readiness](../step-reports/43t1-prep2-offline-runtime-integration-readiness.md) |
| Historical probes and plans | `probes/`, `plans/`, `progress/`, `resources/`, `logs/` | Use the [chronological step-report index](../step-reports/README.md) and repository search; these areas retain prior investigations and negative results. |

## Evidence and privacy

Each document has its own scope and evidence class. External implementation details are not Honda proof; static firmware analysis does not establish runtime behavior; synthetic tests establish only model behavior. The [step-report index](../step-reports/README.md) organizes the history by project era without moving it.

Raw/private captures, firmware extracts, and credentials are intentionally not part of this public archive. The tracked `research/lab/captures/` files are sanitized summaries/redacted event metadata, not raw packet captures. Follow [vehicle testing and data handling](../docs/safety/vehicle-testing.md).
