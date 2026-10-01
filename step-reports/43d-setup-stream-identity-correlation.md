# Step 43D — Honda SETUP stream identity trace

**Scope:** offline Honda static analysis and source-pinned external prior-art review. No vehicle, ADB, Honda runtime, binary modification, Type111 implementation, or live test was used.

## Finding

Honda's recovered SETUP path identifies the requested **stream** by a `type` value. For the supported Type-110 branch, Honda reads `streamConnectionID` as a nonzero uint64 and passes it to the screen AES key/IV derivation. It then opens an ephemeral TCP listener and appends a phone-facing response entry containing constant `type=110` and the selected `dataPort`. It does not appear to echo `streamConnectionID` in that recovered response entry.

The `/info` display descriptor separately contains a numeric `uuid` from the Screen object. The traced Setup stream path does not read or compare this field, and the traced display builder does not read `streamConnectionID`. The request dictionary lookups at Screen object `+0x10/+0x14` remain semantically unresolved. Therefore there is no recovered direct UUID-to-streamConnectionID binding. That is a scoped non-finding, not proof of a protocol-wide absence.

Honda stock skips unsupported type 111 in its Setup loop without adding a Type-111 response entry. The current evidence supports treating `/info` display capability and Setup media-stream identity as separate questions; it does not yet prove how the iPhone selects or correlates a secondary display.

## Honda request/response trace

See the detailed tables in [Honda SETUP stream identity](../research/carplay/honda-setup-stream-identity.md), based on [request parsing](../research/carplay/honda-setup-request.md), [response construction](../research/carplay/honda-setup-response.md), [streamConnectionID and KDF](../research/carplay/stream-connection-id.md), and [mixed-stream dispatch](../research/carplay/honda-mixed-stream-setup.md).

| Field / stage | Recovered Honda behavior | Confidence / boundary |
|---|---|---|
| Request root `streams[]` | Setup iterates each stream dictionary | Confirmed |
| Request `type` | `CFDictionaryGetInt64`; 100/101 audio, 110 screen, other values unsupported/logged | Confirmed for dispatch in this ELF |
| Type-110 `streamConnectionID` | Nonzero uint64 read from request stream dictionary; passed with session master material to screen KDF | Confirmed crypto input; persistent storage not established |
| Other screen setup lookup | CFL dictionary lookup writes a pair to Screen object `+0x10/+0x14` | Dataflow confirmed; key/meaning unknown |
| Type-110 listener | Server socket opens requesting port 0; selected listener port is used in response | Confirmed |
| Type-110 response entry | `{type: 110, dataPort: assigned_port}` appended to mutable response `streams[]` | Confirmed; no streamConnectionID echo observed |
| Type 111 | Unsupported branch logs and continues; contributes no stock response entry | Confirmed static behavior |
| `/info` UUID relation | No read, comparison, or derivation found in these traced Setup paths | `HONDA_UNKNOWN` semantically; binding not found in inspected dataflow |

`timingProtocol`, `timestampInfo`, `latency`, `timingPort`, `eventPort`, `uuid`, `displayUUID`, geometry/view-area fields and similar candidates were not included as confirmed Honda stream keys: the inspected screen Setup path does not establish them. Their absence from this bounded trace is not a protocol-wide negative claim.

## Source-pinned prior art

The new [prior-art note](../research/carplay/setup-stream-identity-prior-art.md) records Apple WWDC19, `carlink_linux`, MHI2 AltScreen, and CPC200 sources with revisions and evidence boundaries.

- Apple describes the public multi-H.264-stream instrument-cluster architecture, view/safe areas, and vehicle-selected stream content. `APPLE_PUBLIC_ARCHITECTURE`; not Honda support evidence.
- `carlink_linux` distinguishes `/info` display/HID capability fields, Setup stream `type`, and a newer iOS 27 FeatureKey mechanism. Its `uuid`/HID `displayUUID` relation is implementation prior art; its modern tokens must not be projected onto Honda.
- MHI2's pinned source passes the original Setup request to stock first, then clones a requested Type-111 descriptor and appends its project-owned response data. `EXTERNAL_PRIOR_ART` for the audited MHI2 firmware only.
- CPC200's pinned documentation presents a log sequence with type 111 setup before nav config/video. `EXTERNAL_PRIOR_ART` for that receiver; it does not establish Honda phone behavior.

This changes the research tactic: map Honda's Setup stream descriptor and response first, then compare possible display/HID identity. Do not assume the display UUID must equal or derive the crypto connection ID.

## Model decision and bounded hypothesis

**Honda model:** `MODEL_D_INSUFFICIENT_EVIDENCE` for the semantic relation between display UUID and stream identity. Honda does confirm two distinct dataflows: display UUID is placed in `/info`; Setup `type` routes the stream, and Type-110 `streamConnectionID` enters screen crypto derivation. A stronger claim that the UUID is specifically presentation-only or HID/input identity is not yet established for Honda.

`HYPOTHESIS`: if the iPhone requests a second stream after evaluating display capabilities, the extension should preserve stock Type-110 setup/response and own only a Type-111 listener, response entry, and independent security/transport state. Which response fields are required, whether unknown peer fields must be cloned, and how Honda's crypto primitive applies to Type 111 remain unknown. MHI2's strategy is informative, not portable implementation proof.

## Readiness and next action

No code or simulator model changed. Type111 response shape, display/stream correlation, jmcs integration, live negotiation, and ExternalDisplay live rendering remain unresolved; all live gates stay closed and LD_PRELOAD remains parked.

The Setup response path is sufficiently recovered to study a **stock-first mutation boundary**: identify the safest static post-Setup/pre-serialization integration seam, its ownership/lifetime constraints, and how a failed project-owned Type-111 append could return the untouched stock response. Do not implement a hook or open a live gate.

## Decision gate

PRIOR ART MODEL: WRITTEN

SETUP REQUEST TRACE: PARTIAL

SETUP RESPONSE TRACE: PARTIAL

STREAMCONNECTIONID TRACE: PARTIAL

TYPE FIELD TRACE: COMPLETE

UUID CORRELATION: NOT FOUND

DISPLAY UUID ROLE: UNKNOWN

HONDA MODEL: MODEL_D_INSUFFICIENT_EVIDENCE

TYPE111 RESPONSE SHAPE: UNKNOWN

IMPLEMENTATION READY: NO

LIVE TEST READY: NO

JMCS INTEGRATION READY: NO

EXTERNALDISPLAY LIVE RENDER READY: NO

LD_PRELOAD: PARKED

NEXT STATIC QUESTION: What is the safest Honda post-Setup/pre-serialization seam for an optional project-owned Type-111 response while preserving the original stock response on every failure?
