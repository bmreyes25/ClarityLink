# CL-R9 genuine Honda integration feasibility

**Decision:** both OEM boundaries remain disabled. Existing evidence supports
the Type110 receiver path and a synthetic Type111 laboratory pipeline, but it
does not establish a Honda-authorized Type111 extension or a supported way to
submit arbitrary frames to Honda Display 1. No vehicle, Honda runtime, ADB, or
live iPhone operation was performed for CL-R9.

## Evidence and receiver gate

| Finding | Classification | Evidence and limit |
|---|---|---|
| Honda owns the factory USB/iAP2/MFi and AirPlay receiver-session lifecycle in `jmcs`. | **STATICALLY OBSERVED** | Existing receiver/session studies and `step-reports/43t1-r6c-honda-auth-substrate-reuse.md`. No separately callable authenticated-session handoff is established. |
| Honda's inspected `/info` path serializes one main-display descriptor. Its producer calls the main-screen accessor once; fields include UUID, FPS, pixel/physical dimensions, features, and EDID. | **STATICALLY OBSERVED** | `step-reports/28-honda-display-capability-gating.md`, `step-reports/43a-honda-info-type111-differential.md`, and `research/carplay/honda-info-type111-differential.md`. No second display descriptor, role field, or Type111 advertisement is established. Absence in the audited path is not proof of global absence. |
| The known Honda Type110 SETUP response includes `{type: 110, dataPort}` and preserves stock ownership. | **STATICALLY OBSERVED** | `step-reports/27-honda-setup-send-path.md` and `step-reports/43r-type111-setup-listener-contract.md`. This proves the inspected local Type110 path, not iPhone acceptance of a modification. |
| The audited Honda SETUP path does not establish Type111 dispatch, schema, authorization, transport delegation, or teardown. | **UNKNOWN / NOT ESTABLISHED** | The existing `HondaStaticType110Adapter` deliberately raises `EvidenceRequired("honda_type111_setup_dispatch")`; its Type111 response path separately requires `honda_type111_response_schema`. Keep both guards. |
| A lab fixture can exercise independent Type110/Type111 listeners, generation ownership, H.264 decode, Binder/PFD delivery, and warning-gated rendering. | **LABORATORY MODEL** | CL-R5 through CL-R7 source and the CL-R4/CL-R7 API17 receipts in `docs/status/current.md`. These receipts do not grant Honda or MFi authority. |

**RECEIVER GATE: `RECEIVER_AUTHORIZED_SPEC_REQUIRED`.** The exact missing
contract is an authorized Honda receiver-owner extension specification that
defines: capability creation and phone-facing advertisement; Type111 SETUP
dispatch and request/response schema; authenticated parent-session binding;
stream-connection identity and generation binding; transport/security
delegation; Type110 coexistence; and disconnect/teardown ownership. No ClarityLink
authority bridge to Honda is enabled or implemented. The lab's synthetic
authority remains explicitly separate.

## Evidence and display gate

| Finding | Classification | Evidence and limit |
|---|---|---|
| Android exposes logical Display 1 at 800×480 in the retained diagnostics. | **STATICALLY OBSERVED** | `research/navigation-safe-area.md`; this is the Android canvas, not the factory cluster's Navigation viewport. |
| `ExternalDisplayOutService` owns the external-display windows; the AP Binder provides display/control/status operations. | **STATICALLY OBSERVED** | `research/display/externaldisplay-api-surface.md`. The audited Binder interface has no View, Surface, bitmap, pixel-buffer, H.264, or stream-FD submission method. Runtime access grants were not established. |
| HondaHack historically renders a View by Xposed injection into a private ExternalDisplay root. | **STATICALLY OBSERVED (third-party method)** | `research/hondahack/hondahack-display-path.md`. This is not an authorized/public ClarityLink API and supplies no Honda warning or restoration contract. |
| The actual factory Navigation safe area, physical transform, and pixel format are known. | **UNKNOWN** | `research/navigation-safe-area.md` distinguishes the 800×480 Android canvas from a HondaHack layout-local bitmap rectangle; neither gives the factory Navigation bounds. |
| Warning precedence, frame withdrawal, and safe restoration can be controlled through a supported arbitrary-frame API. | **UNKNOWN / NOT ESTABLISHED** | No such admission API or contract was recovered in the audited service boundary. Android `Presentation` or logical display discovery alone does not establish Honda ownership. |

**DISPLAY GATE: `DISPLAY_SUPPORTED_PATH_NOT_FOUND`.** This means the bounded,
available service/interface evidence contains no supported arbitrary-frame
admission path. It does not claim that no private or owner-only mechanism exists.
The precise missing contract is a Honda-authorized Display 1 interface
specification covering owner admission, Navigation eligibility, geometry and
pixel format, warning priority, frame withdrawal, owner-loss behavior, and
restoration of the original factory presentation.

`src/claritylink-renderer/honda_output.py` is an inert boundary. It has no Honda
handle, cannot be enabled by caller metadata, and returns
`EVIDENCE_REQUIRED_HONDA_DISPLAY_ADMISSION_API` for attach/submit. The existing
API 17 `Display1OutputBackend` remains a renderer that requires a supplied Host;
root acquisition is not implemented. `safeForHonda()` remains `false`.

## Offline integration and verification scope

The existing CL-R7 integration composes explicit lab authority, Type111 media,
Binder/PFD output, and the CL-R6 warning-gated host. It is synthetic at both
OEM edges. The new parameterized
`tests/integration/test_cl_r9_evidence_boundaries.py` composes a MODEL_ONLY
session with synthetic Type110/Type111 stream identities and a warning-gated
output fixture. It checks exact stream IDs and generations, Type111 frame
delivery and warning withdrawal/fresh-frame recovery, stale-identity
rejection, secondary teardown, Type110 continuation, and complete cleanup. In
the separate Honda-boundary test, the static Type111 SETUP adapter rejects
Type111 and the Display 1 adapter rejects attach even with asserted owner
metadata without calling a sink. These adapter classes have no reference to
the lab `Receiver` or synthetic authority, so no fallback path is implemented;
the test does not model a shared ingress orchestrator. The lab fixture uses
already-decoded, valid 1×1 synthetic PNG frames; actual H.264 decode and API17 delivery
remain supported only by the existing CL-R7 receipts. These tests do not
establish Honda compatibility.

## Smallest decisive external evidence request

Request these two specifications from Honda, the authorized receiver vendor,
or the authorized head-unit integration owner:

1. **Receiver:** a supported extension point and versioned Type111 contract,
   including exact capability encoding, SETUP schema and response, the API
   that supplies genuine authenticated session ownership, stream/security
   delegation, coexistence with Type110, and teardown/error semantics.
2. **Display:** a supported frame/View admission API and versioned contract,
   including caller authorization, owner/session lifecycle, Navigation
   eligibility, exact coordinate and pixel-format contract, warning
   arbitration, withdrawal, and factory-presentation restoration.

No raw firmware, proprietary captures, identifiers, or credentials are part of
this request. Static research is exhausted at the exposed-boundary level; a
new broad extraction is not justified without a specific authorized source or
owner-provided specification.

## Staged future validation plan

All stages require separate authorization before execution. No stage was
started in CL-R9.

### Stage 1 — independent interface review

- **Prerequisites:** owner-provided receiver and display specifications;
  source provenance; named reviewers authorized to see the material.
- **Operations:** compare each document to the exact fail-closed adapter and
  verify version, ownership, identity, warning, and restoration semantics.
- **Evidence:** signed-off contract matrix, unresolved-field list, and review
  findings with source references; keep confidential materials private.
- **Stop:** missing version/authority, unclear Type110 behavior, or undefined
  warning/restore path.
- **Pass:** both contracts define every required boundary field and authorize
  the proposed use. **Fail:** either interface is unsupported or ambiguous.
- **Restoration:** not applicable; read-only document review.
- **Approvals:** Honda/receiver and display interface owners plus independent
  security and automotive-safety reviewers.

### Stage 2 — authorized bench contract setup

- **Prerequisites:** Stage 1 pass; written bench authorization; spare/test
  receiver or vendor-approved development environment; isolation, power, and
  recovery plan; no customer vehicle.
- **Operations:** configure only documented endpoints, validate owner/session
  admission and withdrawal with non-navigation test frames, verify Type110
  continuity, warnings, and factory UI restoration.
- **Evidence:** versioned config, bench inventory, event trace, warning and
  disconnect receipts, restoration receipt, and exact source/build hashes.
- **Stop:** unexpected Type110/audio/control loss, warning overlap, stale
  frame, owner ambiguity, or failed restoration.
- **Pass:** all documented boundary behaviors and restoration criteria pass;
  otherwise fail and keep adapter disabled.
- **Restoration:** follow vendor-documented reset/recovery procedure; never
  infer reversibility from firmware backups.
- **Approvals:** interface owner, lab safety owner, security reviewer.

### Stage 3 — genuine authenticated Type111 on supported test hardware

- **Prerequisites:** Stage 2 pass; supported test receiver; genuine authorized
  iPhone/session; approved Maps/Waze test account and navigation route; capture
  handling and privacy plan; known-good Type110 baseline.
- **Operations:** negotiate through the documented receiver, prove genuine
  authenticated Type111 advertisement/setup, display independent real CarPlay
  navigation, exercise warnings/disconnect, and verify Type110/audio/Siri/calls
  and steering controls remain intact.
- **Evidence:** receiver-authorized negotiation record, stream identity and
  generation receipts, independently reviewed video/display evidence, warning
  and teardown traces, and restoration receipt. Synthetic frames do not count.
- **Stop:** authentication ambiguity, unsupported app negotiation, warning
  collision, factory behavior regression, stale display, or any restore error.
- **Pass:** both genuine content and every preservation/safety criterion pass;
  no passing lab fixture can substitute.
- **Restoration:** stop the test session and restore the documented stock
  receiver/display state; verify it before returning hardware.
- **Approvals:** receiver/display owners, iPhone test owner, security and
  automotive-safety reviewers.

### Stage 4 — separately approved parked-vehicle evaluation

- **Prerequisites:** Stage 3 pass; a separate explicit written vehicle-test
  authorization; independently reviewed hazard analysis and test procedure;
  qualified vehicle operator; parked, secured vehicle; abort observer; verified
  OEM restoration and recovery path.
- **Operations:** only the separately approved, bounded checks. Begin and remain
  parked; do not perform road testing. Validate factory instruments and warning
  visibility throughout, then restore and recheck stock behavior.
- **Evidence:** authorization, vehicle/config identity, instrument and warning
  observations, genuine Type111 evidence, abort/restore trace, and independent
  sign-off. Protect any private vehicle data.
- **Stop:** movement, warning/instrument interference, unexpected control/audio
  behavior, loss of receiver ownership, or inability to restore.
- **Pass:** all predeclared criteria pass and stock operation is independently
  verified after restoration; otherwise disable and remove the test integration.
- **Restoration:** use only an independently validated OEM procedure and verify
  all factory displays, instruments, warnings, audio, calls, and controls.
- **Approvals:** vehicle owner, Honda-authorized integration owner, qualified
  operator, and independent automotive-safety reviewer.

## Feasibility conclusion

Genuine secondary-display CarPlay navigation is **not supportable from the
currently established Honda contracts**. The current software can accept a
legitimate future interface specification behind the two inert boundaries;
until then, the Type111 receiver adapter and Honda Display 1 output remain
disabled. No physical compatibility or safety claim is made.
