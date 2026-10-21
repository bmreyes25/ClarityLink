# CL-HH-06B — Display 1 data-flow analysis

**Verdict: B — new technical understanding, but NO-GO.** Offline static evidence describes a pixel-casting route and a distinct semantic/widget route. It does not establish a supported renderer-admission interface, safe ownership/revocation, warning priority, or crash-safe restoration. `safeForHonda() == false`.

## Scope and evidence handling

This is a sanitized architectural report based on the preserved HondaHack Pro 7.7.7 artifact, REA/JADX static inspection, and explicitly identified earlier private static notes. Exact class/method names, hook signatures, transaction details, private evidence IDs, and call graphs are retained only in authorized private storage. No APK was patched or executed, no vehicle service was invoked, and no vehicle was connected.

Labels: **OBSERVED_STATIC** means directly returned by static artifact inspection; **OBSERVED_HISTORICAL_RUNTIME** is limited to a prior preserved observation; **INFERRED** is a relationship or likely consequence not directly proven end to end; **UNKNOWN** lacks sufficient evidence; **UNSUPPORTED** was not found in the reviewed artifact/documentation; **REQUIRES_AUTHORIZATION** would need a separately authorized environment or action.

## Screen-casting pipeline

```mermaid
flowchart LR
  U[User enables cast] --> F[Feature state and refresh scheduling]
  F --> P[Android system screenshot producer]
  P --> B[Display 0 frame represented as bitmap]
  B --> M[Shared-memory buffer and message transport]
  M --> C[HondaHack receiver-side consumer]
  C --> I[Bitmap/ImageView update]
  I --> X[Xposed in-process insertion into Honda display host view tree]
  X --> D[External-display host presents on Display 1]
  F -. normal stop / page transition .-> T[Callback and transport cleanup]
  P -. producer or process failure .-> Q[Recovery outcome unknown]
  C -. consumer or host failure .-> Q
```

| Stage | Finding | Class | Limit |
|---|---|---|---|
| Start action and feature initialization | A user preference changes the cast state and schedules refresh work. | OBSERVED_STATIC | Does not prove the full UI-to-frame path under runtime conditions. |
| Producer selection | Screenshot acquisition is requested through an Android system screenshot service in the observed static route. | OBSERVED_STATIC | Permission, timing, and successful capture are not runtime-verified here. |
| Frame acquisition and representation | Earlier private static evidence describes a Display 0 screenshot represented as an ARGB bitmap at a fixed source size. | OBSERVED_STATIC (historical static note) | This is source-side metadata, not proof of final cluster crop or pixels. |
| Buffer copy and transport | Earlier private evidence describes a shared-memory buffer and message/file-descriptor transport with initialization, update, and close phases. | OBSERVED_STATIC (historical static note) | Exact protocol details are private; no transport was exercised. |
| Consumer and bitmap/view update | Selected receiver code creates or updates bitmap-backed image content. | OBSERVED_STATIC | Successful frame delivery and UI-thread behavior are not runtime proven. |
| Host admission and output | Static Xposed integration inserts app-owned content into a Honda external-display host's view hierarchy; the host is associated with Display 1. | OBSERVED_STATIC | Does not establish a supported public API, admission authorization, actual aperture, or guaranteed display output. |
| Normal teardown | Normal stop/page transitions and observed disconnect callbacks include cleanup paths. | OBSERVED_STATIC | Callback execution is not guaranteed after process death or host restart. |
| Abnormal cleanup | Process death, stale frame disposal, host restart recovery, and factory-content restoration are not proven crash-safe. | UNKNOWN | Requires separate lifecycle and recovery evidence; no vehicle testing authorized. |

The dotted arrows indicate inferred failure outcomes, not observed behavior.

## Feature data-source and rendering matrix

| Feature | Primary data form | Renderer/consumer indicated by evidence | Vehicle/service relationship | Status |
|---|---|---|---|---|
| Screen casting | Captured pixels / bitmap frames | Bitmap-backed image content inserted into the external-display host | Screenshot producer plus host-view integration | Static path observed; complete runtime delivery inferred. |
| Advanced Meter | Semantic/widget inputs, including instrument values and navigation-related presentation | Custom in-process views using the shared injected host integration | Vehicle-data consumers may supply values; individual read side effects not fully classified | Shared host mechanism observed; not the screen-cast bitmap pipeline. |
| Factory Navigation integration | Navigation-page state and semantic content | Factory Honda navigation UI/content | Honda-owned navigation and services | Exact data flow and overlap with injected rendering are partially unknown. |
| Waze turn-by-turn | Semantic maneuver/guidance information is a distinct category from screen pixels | Evidence does not establish that HondaHack's Waze path is a bitmap stream; head-unit Waze observations are separate evidence | Potential navigation-data/service path; source and authority are not established here | Relationship to this APK's specific rendering route remains unknown. |
| Honda system-service interaction | Structured service/vehicle data or commands | Service clients feeding feature logic or widgets | Some methods may be read-only, control-capable, or mixed | Classify per method and transitive effects; a “get” name is not proof of purity. |

Thus, the observed screen cast is a pixel producer, while Advanced Meter is a semantic/widget renderer. Factory Navigation is Honda-owned navigation content. Waze TBT must be treated as semantic navigation data unless a frame source is directly evidenced. The artifact does not establish that these features share one data/rendering pipeline.

## Xposed and display ownership model

Static indicators and selected entry-point code show conditional Xposed integration into selected application processes, with hooks registered during package/process load and view operations performed in the host process. The observed Display 1 route depends on privileged in-process access to Honda-owned view structures, rather than a documented external renderer client contract.

| Question | Finding |
|---|---|
| Target processes | Selected Honda application processes are targeted conditionally. Exact process identifiers and hook signatures remain private. |
| Lifecycle | Entry-point handling occurs at package/process load; registration is conditional. Normal callbacks offer cleanup opportunities. |
| In-process vs cross-process | Host view insertion occurs in the Honda host process; frame production/transport includes cross-process communication. |
| Content ownership | Honda owns the host hierarchy; injected feature content is app-supplied. A formal shared ownership or lease contract is not established. |
| Callback registration and cleanup | Normal registration and detach/stop paths are statically visible. Universal callback delivery is not guaranteed. |
| Failure assumptions | Restart ordering, duplicate attach handling, stale content, and crash recovery remain unknown. |
| Caller authorization | No supported third-party caller authorization contract established. |
| Revocation/lease | No ownership lease, revocation handshake, or host-enforced lifecycle contract established. |

This model is an architectural description, not an implementation recommendation.

## Vehicle interface classification

| Boundary | Classification | Evidence limit |
|---|---|---|
| Screenshot request and Android display capture | READ_ONLY_OBSERVED | Reads system display pixels; exact permission and capture restrictions are not runtime checked. |
| Host view insertion | MIXED | Changes UI state in a Honda-owned process; its relationship to vehicle-control state is not established. |
| Honda system-service clients used by meter/features | UNKNOWN / potentially MIXED | Must trace downstream effects for each method; getter naming alone is insufficient. |
| Navigation-related service/data interfaces | UNKNOWN | Static semantic flow does not establish that downstream consumers are side-effect free. |
| Vehicle-bus mutation | UNKNOWN | No invocation was made; absence of an observed write in selected paths is not proof of a bus-free path. |

No vehicle-facing method was invoked. Any read-like call that triggers listeners, mode changes, wakeups, or downstream service effects would need separate side-effect analysis.

## Safety and restoration failure matrix

| Event | Normal path evidence | Abnormal behavior / restoration status |
|---|---|---|
| User exits feature | Static stop and cleanup paths exist. | Cleanup completion depends on callbacks and process state; no runtime guarantee. |
| Navigation page changes | Static page/feature transition handling exists. | Exact physical viewport bounds and restoration timing are unknown. |
| Factory warning or interrupt | One historical Door Open example is limited evidence of preemption behavior. | Universal warning priority, composition, or precedence is not proven. |
| Producer dies | Normal close signaling is represented in the static protocol. | Delivery of close after abrupt death and stale-frame cleanup are unknown. |
| Consumer dies | Normal disconnect cleanup exists. | Restart/rebind behavior and removal of already attached content are unknown. |
| Honda display host restarts | Load-time hooks may register again on a new process lifecycle. | Duplicate attachment prevention, ordering, and recovery are not guaranteed. |
| Repeated attach/detach | Normal lifecycle code has attach/detach handling. | Idempotence under races and resource release are unverified. |
| Factory content restoration | Normal paths indicate removal/transition behavior. | Crash-safe restoration and host-owned recovery are not established. |

## Interface decision

1. **Documented external renderer admission interface?** UNSUPPORTED by reviewed evidence.
2. **Observed drawing access dependent on privileged in-process code?** Yes, OBSERVED_STATIC for the reviewed path.
3. **Caller authorization established?** UNKNOWN; no supported authorization contract found.
4. **Ownership lease or revocation contract?** UNSUPPORTED by reviewed evidence.
5. **Physical Navigation viewport bounds established?** UNKNOWN.
6. **Warning priority proven?** No. A limited historical Door Open observation cannot establish universal priority.
7. **Factory restoration crash-safe?** UNKNOWN; not proven.
8. **Relevant path free of vehicle-bus mutation?** UNKNOWN; selected static evidence and no invocation do not prove this.
9. **Material change to CL-R10B/CL-R10C?** Adds a more specific observed pixel pipeline and separates it from semantic/widget rendering. It does not change their no-supported-interface conclusion or NO-GO decision.

**Decision: retain NO-GO.** No supported API or adequate safety contract has been established. Do not infer a possible implementation from private technical access.

## Findings compared with prior display research

- **CL-R10B** established the bounded display-ownership result: Honda owns the host view roots, reviewed evidence did not establish a supported arbitrary-frame admission/revocation contract, and the single warning observation has limited generality. This report adds a source-backed description of HondaHack's bitmap producer-to-host path, while keeping the same authorization and restoration gaps. See [CL-R10B](cl-r10b-display-ownership.md).
- **CL-R10C** retained NO-GO pending an authorized host contract, warning/preemption evidence, teardown, recovery, and a safe bus boundary. This report separates HondaHack's pixel-copy path from semantic/widget rendering; it does not satisfy any of those gates. See [CL-R10C](../native/cl-r10c-integration-architecture.md).
- The more specific static path is not evidence of a supported interface. It does not establish caller authorization, physical viewport geometry, process-death cleanup, universal warning priority, or bus purity.

## Highest-value unknowns and CL-SYS-01 questions

- Does Honda provide a documented external renderer admission API with caller identity checks, explicit display/viewport bounds, and host-owned lifetime enforcement?
- What ownership, revocation, and recovery contract applies if the producer, renderer, or host process exits unexpectedly?
- How are factory navigation content and safety warnings prioritized, and is that policy enforced by the host independently of third-party lifecycle callbacks?
- Which Honda service interfaces are observational, control-capable, or mixed after following their transitive effects?
- Can the supported interface guarantee no vehicle-bus mutation for a renderer-only client?
- What evidence defines the physical navigation viewport and scaling/crop policy for each supported head-unit configuration?
- Does the host restore factory content after process death, repeated attach/detach, and host restart without relying on the injected client?

## Limitations

This is static analysis of one preserved version. It does not prove runtime behavior, installation authenticity, compatibility with other builds, warning arbitration, screen geometry, service side effects, crash recovery, or safe vehicle operation. The live Codex MCP Android provider still requires restart/revalidation; successful REA CLI calls and a prior Ghidra smoke test are not substitutes for that check. Private evidence records remain outside public GitHub. No APK modification, injection execution, Honda ADB, vehicle connection, private service invocation, or CAN activity occurred.
