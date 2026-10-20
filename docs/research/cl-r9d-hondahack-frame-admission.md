# CL-R9D — HondaHack cluster presentation and frame admission

## Decision

**No supported frame-admission interface is documented.** HondaHack's public material advertises screen casting, cluster meter information, and turn-by-turn guidance, but gives no caller-authorized image/Surface submission API, warning priority, output ownership, or teardown/restoration contract. This public report uses only public HondaHack pages and does not publish Honda/APK-derived implementation findings.

The HondaHack integration boundary remains disabled. `safeForHonda()` remains false. This is offline research. It does not install, launch, or operate HondaHack or a vehicle. No APK, decompiled code, capture, credential, device identifier, or private Honda implementation detail is included here.

## Public compatibility and behavior

HondaHack's feature overview describes rooting the Honda head unit and includes Clarity among supported vehicles. Its Advanced Information tutorial expressly targets Civic, CR-V, and Clarity. It instructs users to add and select the factory Navigation page before enabling instrument-cluster settings. The tutorial describes Waze turn-by-turn directions and advises disabling Advanced Meter to use Android Auto turn-by-turn. The release notes attribute Advanced Meter, compass/vehicle information, Waze turn-by-turn, and central-display-to-cluster screen casting to version 6.7.9, and later mention black-screen fixes after steering-wheel and startup transitions.

These are vendor-published product claims, not an OEM interface specification. They do not establish exact compatibility for every Clarity model/year/trim/firmware, including the precise 2018 Clarity PHEV Touring / MY16ADA combination. The Clarity-specific tutorial establishes a documented Advanced Information feature scope, but the public materials do not provide an exact Screen Casting support matrix, frame format, cadence, permissions contract, or warning behavior.

## Feature mechanisms are distinct

| Feature | Publicly documented behavior | Information type | Page/state behavior | Evidence limit |
|---|---|---|---|---|
| Factory Navigation | Factory Navigation is an instrument-panel page that can be added and selected. | Honda's own navigation presentation and guidance. | Page selection is part of factory instrument configuration. | No external frame submission contract is documented. |
| HondaHack Screen Casting | Release notes advertise casting the central display to the instrument cluster. | A screen image is implied by the feature name/description; exact payload and update model are unspecified. | Detailed selection, stop, warning, and restoration behavior is undocumented. | It does not establish Type111 SETUP, negotiated H.264 delivery, or a supported third-party sink. |
| HondaHack Advanced Meter | Tutorial and release notes advertise instrument/compass/vehicle information. | Meter values, text, icons, and navigation-related UI. | User selects the factory Navigation page and enables Advanced Meter options. | Does not establish full-frame video or a public rendering API. |
| Waze turn-by-turn | Release notes advertise advanced Waze turn-by-turn; tutorial says to use Waze on the head unit and notes the Android Auto Advanced Meter toggle. | Guidance/maneuver presentation. | Advanced Meter and Android Auto turn-by-turn have a documented user-facing toggle relationship. | Does not establish H.264 or independent full-frame imagery. |

HondaHack Screen Casting, Advanced Meter, Waze guidance, and factory Navigation are separate features. Public documentation is insufficient to claim continuous video performance or to infer that semantic turn arrows are an H.264 stream.

## Evidence classification

| Candidate | Source / owner | Input, authorization, and lifetime | Warnings, geometry, restoration | Classification and consequence |
|---|---|---|---|---|
| Screen Casting feature | HondaHack release notes and product docs | Public description says central display to cluster. It does not specify a ClarityLink caller identity, image/Surface contract, or authorization method for a third party. | No public safe area, warning precedence, owner-loss, or restoration guarantees. | `PUBLIC_DOCUMENTATION_ONLY`. No supported ClarityLink interface is established by these sources. |
| Advanced Meter / Waze TBT | HondaHack tutorial/release notes | UI and guidance feature claims; no third-party renderer API published. Exact data schema and internal contract unspecified. | Factory Navigation page selection documented; warning and teardown semantics absent. | `PUBLIC_DOCUMENTATION_ONLY`. |
| Honda display admission | No HondaHack public page reviewed documents an OEM display consumer API. | No public caller contract is provided. | No public warning, geometry, or restoration contract is provided. | `UNKNOWN`; feature documentation cannot establish a display-admission API. |
| Ordinary Android external-display API | General Android capability, not a HondaHack or Honda contract. | Honda caller permissions and display admission policy unknown. | Honda geometry, warning ordering, lifecycle, and restoration unknown. | `UNKNOWN`; generic platform capability is not authorization. |

Classification meanings: `SUPPORTED_INTERFACE` requires a documented, authorized Honda/OEM contract; none was found. `OBSERVED_PRIVATE_MECHANISM` and `STATIC_ONLY` are not asserted by this public-doc-only report. `PUBLIC_DOCUMENTATION_ONLY` records a vendor feature/compatibility claim, not an API contract. `UNKNOWN` marks unresolved behavior.

## ClarityLink boundary and offline validation

ClarityLink's synthetic Type111 decoder accepts bounded frames under its lab session/generation contract. That does not grant permission to hand decoded pixels to a Honda display owner. HondaHack's public pages do not identify an authorized frame consumer. The missing boundary is an explicit, authorized frame submission contract tied to the factory display owner, together with warning and lifecycle semantics.

`HondaHackFrameAdmissionGate` records unresolved requirements and always raises `EvidenceRequired`. It is diagnostic only, not runtime output enforcement. It accepts no frame or caller-asserted authority and does not implement an adapter, process hook, or production capability. Its tests use a tiny synthetic byte fixture only to confirm that test data cannot authorize output. The lab renderer/output host remains separate.

## Exact gap and smallest resolving evidence

The closest publicly documented mechanism is HondaHack's screen-casting feature. Its public description is insufficient for product integration because it establishes no ClarityLink caller authorization, accepted frame type, geometry, warning precedence, owner-loss behavior, or factory restoration.

The smallest useful future evidence would be a Honda/OEM-published Clarity-compatible API or sample explicitly authorizing a separately developed renderer to submit a bounded image or Surface to the Display 1 owner, with caller identity requirements and defined warning/lifecycle/restoration behavior. A HondaHack-maintainer-published consumer API and exact supported Clarity model/firmware scope could establish a HondaHack-owned integration contract, but would not alone prove Honda OEM warning guarantees. Another feature claim, screenshot, undocumented integration technique, or root capability is not sufficient.

## Public sources reviewed

- [HondaHack feature overview](https://www.autohack.org/) — advertised vehicle support, root/install model, and top-level feature claims.
- [Display advanced information in the instrument cluster](https://www.autohack.org/display-advanced-information-in-the-instrument-cluster/) — Civic/CR-V/Clarity tutorial scope, factory Navigation page selection, Advanced Meter settings, Waze directions, and Android Auto caveat.
- [HondaHack release notes](https://www.autohack.org/release-notes/) — version 6.7.9 feature claims and later transition-related black-screen fixes.
- [Clarity installation notes](https://www.autohack.org/vehicles/clarity/) — Clarity installation compatibility claim, not a Display 1 API contract.
