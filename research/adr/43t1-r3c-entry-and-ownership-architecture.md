# ADR 43T1-R3C expanded — entry and ownership architecture

- **Status:** accepted for the preserved evidence set, 2026-10-03.
- **Decision:** `R3C_NO_SAFE_RUNTIME_EXTENSION_PATH_FOUND`.
- **Project recommendation:** `ABANDON_RUNTIME_INTERPOSITION_UNTIL_NEW_EVIDENCE`.

## Context and evidence

R2 rejected the four-byte inline callsite patch because safe thread stop/atomicity is unproved. R3A found no usable non-inline Setup mediation. R3B found Honda finalizer/teardown unable to own project children. A narrower earlier R3C session-addressability report is historical. This expanded audit directly inventories 351 preserved ELF paths, the proxy interface, Binder services, screen/device registries, stream dispatch, launch evidence, and pinned external comparators. See the [extension matrix](../runtime/43t1-r3c-extension-path-matrix.md), [proxy](../runtime/43t1-r3c-libcarplay-proxy-interface-audit.md), [service](../runtime/43t1-r3c-honda-service-boundary-audit.md), [dispatch](../runtime/43t1-r3c-stream-dispatch-extension-audit.md), and [external comparison](../runtime/43t1-r3c-external-architecture-comparators.md).

`HONDA_CONFIRMED`: direct Setup/serializer calls stay in `jmcs`; no reviewed module imports those session functions through a dynamic relocation. The real `jmcs`→proxy PLT boundary registers fixed Honda screen/audio/auth callbacks. Screen registration copies one 24-byte record and rejects a second; it provides no Setup request/response. Binder app-status callbacks do not carry the native session or response. Generic `ScreenRegister` appends objects but stock `/info` reads the main entry; Setup and teardown skip Type111. No supported launch slot for project code is preserved.

## Decision among architecture families

| Family | Decision and reason |
|---|---|
| A. Existing additive Honda extension seam | Rejected: no same-session Setup+cleanup observer/registry; generic screen array does not supply the missing call-in. |
| B. Existing dynamic wrapper boundary | Rejected for Setup: actual dynamic proxy registration boundary exists, but no AirPlay Setup/serializer caller import; proxy media callbacks are singleton/too late. |
| C. Existing service/Binder seam | Rejected: app/vehicle status and display controls lack native Setup identity, mutable response, and media ownership. |
| D. Independent project-owned external process | Rejected as integrated Type111 architecture: its own process can own resources, but no Honda entry or correlated response channel exists. |
| E. Unsupported load/interposition | Technically conceivable only with startup/binary change or unsafe interception; prohibited by current boundary and lacking lifecycle coverage. |
| F. No viable runtime-interposition architecture under current evidence | **Selected.** This is a bounded evidence decision, not a theorem about all Honda software. |

## Project-owned cleanup and safety consequences

Any future Type111 design would have to own its candidate graph, listener, accepted sockets, worker, generation, session/connection correlation, rollback, security/decoder state, and lease timer. A project-owned EOF, listener error, transaction failure, worker exit, or bounded lease may close project resources **only after a real Honda entry associates them with the right session**. No such entry is evidenced. Lease expiry cannot repair missing Setup response mutation; a global Honda event lacks generation identity. Process termination may reclaim local descriptors but does not establish vehicle/UI restoration. Partial registration or a worker/session mismatch could leave wrong-generation resources active. `MODEL_ONLY` cleanup guards remain models; no new model is justified by this audit.

Stock Type110 ownership must remain entirely Honda's. Replacing proxy, session delegate, server delegate, global event callback, or dispatch tables could displace its media/control/finalizer path. Consequently no Type110 preservation guarantee exists for a proposed runtime extension. No Honda contact, ADB, runtime memory access/write, listener, Type111 negotiation, or deployment follows from this ADR.

## Rejected alternatives and next evidence

Rejected: inline patch/thread-stop assumption, callback/table replacement, symbol visibility as interposability, app-service status as native session ID, `streamConnectionID` as proven stable session generation, generic screen append as complete alternate display, unknown-type default as Type111 factory, AOSP loader support as Honda launch policy, and MHI2/xcertplay as Honda compatibility. Reopen only with a newly preserved Honda artifact showing an existing additive project entry before response serialization, request/response access, stable session identity, matching cleanup or fully independent bounded project closure, no runtime write to enter, and Honda-only Type110. Until then, pivot architecture work offline away from `jmcs` runtime interposition.

## Model-code gate

`DO_NOT_BUILD_MODEL`: no existing non-replacement session-addressable entry with mutable Setup response and project-owned cleanup was found. The presence of host model infrastructure is not a reason to add another model.
