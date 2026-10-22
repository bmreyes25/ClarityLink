# CL-FACTORY-01 / M3 — Factory Navigation → cluster data flow (sanitized)

Status: IN PROGRESS. Evidence OBSERVED_STATIC (deodexed Java). Offline only. `safeForHonda() == false`.
Exact proprietary identifiers are in private evidence; this report is role/representation level.

## Data flow
```mermaid
flowchart LR
  NavApp[Navigation app + lib] -->|AIDL: navigation AP service| EDAp[ExternalDisplay AP service\n(intake + windowing control)]
  EDAp -->|packetized structured messages| EDOut[ExternalDisplay Out service\n(render host, owns cluster composition)]
  EDOut -->|Android Views onto| D1[Android logical Display 1]
  D1 -. external output (hist. 800x480) .-> Cluster[physical cluster viewport\n(bounds UNKNOWN)]
  Vehicle[vehicle signals / unit info] -. AIDL callbacks .-> EDAp
```

## Representation — structured data, not pixels (key finding)
The cluster Navigation content is delivered as **structured turn-by-turn data**, not as a video/pixel stream of the
navigation app. The dominant payloads are maneuver/turn descriptors: **arrow type, distance-to-maneuver, guidance
points, and road names**, delivered as packetized messages (a multi-packet assembler and feedback/retry timers are
present). Small **drawable/bitmap** assets are used for maneuver icons. The render host turns these values into
**Android Views** in its own hierarchy.

This is architecturally distinct from the HondaHack "Screen Casting" path (a third-party pixel-capture-and-blit
mechanism). The factory Navigation→cluster path is **semantic** (data), and the pixels are produced **host-side**.

## Boundaries (producer → consumer)
| Boundary | Producer | Consumer | Representation | Lifecycle | Access | Evidence |
|---|---|---|---|---|---|---|
| Nav → AP service | Navigation app | ExternalDisplay AP service | AIDL calls | per navigation session | OEM app identity | OBSERVED_STATIC |
| AP → Out host | AP service | Out render host | packetized structured TBT messages | per update | in-platform services | OBSERVED_STATIC |
| Out → Display 1 | Out host | Android Display 1 | Android Views (host-rendered) | host-owned | host process only | OBSERVED_STATIC |
| Display 1 → panel | Android external output | physical cluster | downstream composition | — | — | UNKNOWN (aperture) |

## Failure / cleanup
The AP side carries retry/feedback timers and a destination-retry task; the render host owns view
attachment/removal. Exact teardown/restoration sequencing is traced at method level privately and summarized in
report 08. Host-process death/restart behavior is still being traced.

## Unknowns
- Exact native rendering boundary (whether any compositing occurs outside the Android components we hold).
- Physical cluster aperture/crop (the 800×480 figure is the Android logical display size, not the panel viewport).
