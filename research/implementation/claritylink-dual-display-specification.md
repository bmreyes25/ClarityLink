# ClarityLink dual-display executable specification

**Status:** CL-IMP-00 audit baseline, 2026-10-12
**Repository baseline:** `97624314659b9cd1247ec67d95071278aa24c489`
**Scope:** offline implementation and laboratory validation only. Production Honda integration stays disabled.

## Fixed goal

One conventional multi-display CarPlay session keeps the factory Honda Type110 path on center Display 0 and supplies a distinct, simultaneous Type111 navigation stream from the connected iPhone to the cluster Navigation region on Display 1. Display 0 retains primary video, USB/iAP2 ownership, accessory authentication, audio, microphone, Siri, calls, and controls. Display 1 is an additive path. CarPlay Ultra, screen mirroring, synthetic maps, Android Auto, and independently calculated navigation are not substitutes for the requested end state.

## Evidence labels

| Label | What it establishes |
|---|---|
| `SOURCE_IMPLEMENTED` | Project source code exists; this alone says nothing about target compatibility. |
| `HOST_TESTED` | Executed against host tests, models, mocks, or generated fixtures. |
| `API17_EMULATOR_TESTED` | Executed on an isolated API 17 emulator. |
| `ARMV7_BUILT` | Cross-built for ARMv7/API17; not proof of target execution. |
| `STATIC_HONDA_EVIDENCE` | Bounded artifact-backed observation of Honda software, not runtime authorization or iPhone interoperability. |
| `EXTERNAL_PRIOR_ART` | External project/documentation evidence, including HondaHack; not an installable ClarityLink interface. |
| `UNPROVEN_EXTERNAL_INTERFACE` | Requires new Honda/iPhone evidence or a supported integration boundary. |
| `NOT_IMPLEMENTED` | No suitable project-owned implementation was found in this audit. |

Generated/replay data must remain labeled synthetic. A mock or a successful local build cannot promote a claim to Honda-confirmed or authentic-stream status.

## Executable invariants

`claritylink-component-inventory.json` is the machine-readable source for the fixed architecture and component ledger. The acceptance tests under `tests/implementation/` reject any specification that:

1. transfers Display 0's primary session, Type110 stream, or stock control ownership to ClarityLink;
2. describes a mirrored Display 0 frame as Type111;
3. describes synthetic/replay navigation as authentic iPhone CarPlay content; or
4. treats mock, source, emulator, or build evidence as proof of Honda integration.

Primary ownership is represented as structured fields, not inferred from prose. The inventory has no accepted Honda-integration or authentic-iPhone-Type111 evidence records at this baseline. Therefore no evidence label can establish either claim until a separately reviewed, provenance-bearing record is added.

The production feature gate must remain off until the missing session/security delegation, Honda renderer admission, display safe-area, and warning-priority interfaces have genuine evidence and separate authorization.

## Current implementation boundary

The repository has substantial offline foundations: a Python custom receiver and replay path, /info and capability models, Type111 setup contracts, security-provider interfaces, screen parsing and H.264 host decoding, Android API17 display admission candidates, Java CPU-frame rendering, lifecycle models, an offline dual-display demo, and ARM/API17 tooling. Some Android components are scaffolds or diagnostic applications rather than the requested production adapters. The audited inventory records exact files and tests.

HondaHack's published/static path demonstrates an in-process custom `View` inserted into Honda's ExternalDisplay window hierarchy, including image-based screen casting. ClarityLink's current renderer backend deliberately accepts an injected host and viewport; obtaining Honda's root through an approved interface is not implemented. Its observed layout dimensions are not a verified physical cluster safe area. No stock process modification or hook installation is in scope.

The existing Android `SecondaryDisplayHost` is a `Presentation` admission candidate, not the requested completed independent application adapter. No project-owned ExternalDisplay-style host/overlay IPC system or bounded shared-memory decoded-frame channel was found in the audited source. These become explicit implementation milestones.

## Completion criteria

The end-to-end lab must render distinct, labeled synthetic primary and secondary frames simultaneously while preserving primary ownership through secondary failure. It must reject stale generations; bound frame memory; clear secondary output on warning preemption/disconnect; and tear down only resources it owns. A future genuine iPhone Type111 stream must be separately marked and cannot be inferred from the lab demo. A future Honda integration gate must independently establish session delegation/security authority, app/view admission, safe-area geometry, warning priority, and restoration behavior.

See [component inventory](claritylink-component-inventory.json) and [gap closure plan](claritylink-gap-closure-plan.md).
