# ADR 43T1-R4A — post-interposition architecture pivot

- **Status:** accepted for offline planning, 2026-10-03.
- **Primary direction:** `PIVOT_TO_CLUSTER_NAV_RENDERER`.
- **R4A decision:** `R4A_PIVOT_TO_CLUSTER_NAV_RENDERER`.
- **Project recommendation:** `GO_FOR_R4B_OFFLINE_RENDERER_MODEL`.

## Context

R3C found no safe additive entry/ownership architecture in the preserved Honda receiver and recommended `ABANDON_RUNTIME_INTERPOSITION_UNTIL_NEW_EVIDENCE`. The user-level goal remains useful cluster navigation while the center CarPlay/audio path stays stock. [Display 1 evidence](../runtime/43t1-r4a-cluster-rendering-architecture.md) confirms an Android canvas and HondaHack composition precedent but **no supported independent ClarityLink display entry**, physical Navigation safe area, or on-car coexistence proof. [Navigation-source audit](../runtime/43t1-r4a-navigation-data-source-audit.md) finds public APIs for an app's own route steps, not a reviewed public feed of Apple Maps/Waze's active guidance.

## Decision

Design a **non-Type111, turn-card-first cluster renderer** as an offline model. R4B should use synthetic/manual steps and test bounded state transitions, clipping uncertainty, stale-route clearing, and human-readable fallback. Its later production route source should be user-controlled and independent, chosen only after provider terms, privacy and phone/Android channel feasibility are reviewed. Keep `jmcs`, Honda CarPlay callbacks, Type110 media, and stock center UI outside this architecture.

This is the best next *research/UX path*, **not a deployable Honda architecture**. A public Android API-17 `Presentation` exists (`DOCUMENTED_ANDROID`), but Honda Display 1 presentation flag/access, window priority, safe area and warning coexistence are `UNKNOWN`. HondaHack's Xposed-injected View (`HONDA_OBSERVED`/third-party static) is a rendering precedent, not a supported app interface. The R4B model must label all such boundaries.

## Choices considered

| Choice | Decision |
|---|---|
| `PIVOT_TO_CLUSTER_NAV_RENDERER` | **Selected** for offline, turn-card-first work; minimizes CarPlay coupling and permits safe UX/state evaluation. |
| `PIVOT_TO_PHONE_COMPANION_ARCHITECTURE` | Keep as later data/channel subarchitecture. It cannot by itself solve cluster display access. |
| `PIVOT_TO_EXTERNAL_ROUTING_PROVIDER` | Keep as later source choice. It cannot by itself solve display access or prove live guidance. |
| `PAUSE_CLARITYLINK_UNTIL_NEW_HONDA_EVIDENCE` | Not selected for *offline* UX research; would become appropriate if independent display access is disproven. |
| `REOPEN_RUNTIME_INTERPOSITION_ONLY_WITH_NEW_EVIDENCE` | Gate only, not current direction; R3C NO-GO remains controlling. |

## Consequences, safety and remaining unknowns

The model cannot show an actual Honda cluster pixel, validate physical safe bounds, or ensure driver glanceability. It must suppress stale/mismatched instructions, avoid road-use claims, keep fixture location data synthetic, and demonstrate fallback rather than silently retaining guidance. External routing services may charge money and receive coordinates; keys must stay out of source/logs. Apple Maps/Waze screen or notification scraping is rejected. Do not send Honda TBT Binder messages; those interfaces may interact with vehicle systems and do not provide this renderer path.

The stock center CarPlay path is untouched by the **design**, while on-device coexistence remains untested. No Honda/ADB/runtime work or deployment is authorized. [Architecture matrix](../runtime/43t1-r4a-architecture-pivot-matrix.md) records comparative verdicts; [new-evidence gate](../runtime/43t1-r4a-new-evidence-gate.md) defines the separate bar for revisiting receiver integration.
