# Step 42B — Type111 architecture decision

**Scope:** offline architecture selection from preserved Honda evidence and Step 42A. No vehicle, ADB, deployment, binary execution, or Type111 activation occurred.

## Decision

**Target architecture:** jmcs integration owns the authenticated CarPlay control/session boundary and Type111 receiver state; a narrow renderer adapter in the ExternalDisplay host presents decoded secondary frames. Stock Type 110 remains delegated to Honda and unchanged. This is an architecture choice, not a statement that either integration seam is currently available.

**Current active work:** digital-twin/offline model development. **LD_PRELOAD:** parked fallback only. No live Type111 or companion test is ready.

## Evidence and boundaries

- **Honda confirmed:** `/info` serializes a `displays` array, while the stock builder emits one descriptor. Type 110 Setup consumes a nonzero `streamConnectionID`, creates a data listener and returns `type` plus `dataPort`; the ID participates in the screen crypto derivation. No display-UUID relationship was found.
- **Honda confirmed:** unsupported Type 111 is skipped without a response entry. This does not establish that a Type111 extension is impossible; it establishes that the stock handler does not provide one in the traced path.
- **Honda confirmed from reviewed interfaces:** ExternalDisplayOutService owns Display 1's View hierarchy and its exported service returns null from `onBind`. The separate ExternalDisplay AP Binder and CarPlay AP Binder expose no reviewed frame/Surface or Type111/session/security handoff.
- **Prior-art hypothesis only:** MHI2 adds a secondary response after stock Setup and uses a distinct stream/listener state. Those fields and crypto behavior are not Honda facts.
- **Unknown:** Type111 response schema, display-to-stream correlation, Honda Type111 key derivation, a supported jmcs load seam, and a supported renderer handoff.

## Candidate outcome

An external proxy is not selected: no request/response redirection or session-material transfer path is proven, and the observed jmcs sockets are not attributed to the Setup path. A replacement receiver is too broad and has no evidence for preserving Honda center CarPlay. ExternalDisplay-only work can exercise synthetic rendering but cannot cause an iPhone Type111 request. The twin remains the only immediately executable route; it advances state/lifecycle correctness but cannot prove Honda compatibility.

## Decision gate

```text
HONDA TYPE111 REQUEST HANDLING: SKIPPED
SUPPORTED EXTERNALDISPLAY COMPANION API: NO
CARPLAYSERVICE TYPE111 HANDOFF: NO
GENUINE TYPE111 REQUIRES JMCS OR PROXY: YES
INDEPENDENT RECEIVER FEASIBLE: UNKNOWN
NETWORK PROXY FEASIBLE: UNKNOWN
JMCS INTEGRATION REQUIRED: YES
BEST CONTROL-PLANE SEAM: JMCS
BEST RENDER SEAM: EXTERNALDISPLAY_INJECTION
ACTIVE ARCHITECTURE: JMCS_INTEGRATION
LD_PRELOAD STATUS: PARKED
OFFLINE MODEL UPDATE: NO
COMPANION TEST: NOT READY
TYPE111 LIVE WORK: NOT READY
BIGGEST BLOCKER: no proven jmcs code-entry seam or supported ExternalDisplay frame handoff, with Honda Type111 response/security contract still unknown
```

`ACTIVE ARCHITECTURE` names the selected target design. It does not mean an active vehicle implementation exists; the current workstream is the digital twin.

## Next milestone

Build an offline jmcs integration contract: identify the minimum `/info` and Setup mutation boundaries, stock-first Type 110 invariants, Type111 listener/session inputs, and an explicit ExternalDisplay frame-handoff contract. Keep every Type111 field marked hypothesis/unknown pending Honda evidence. Do not reopen preload work unless new evidence changes its parked status.
