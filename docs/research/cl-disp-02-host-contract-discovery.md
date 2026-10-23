# CL-DISP-02 — Honda Display 1 admission and observation discovery

**Scope:** Phase 3 display-contract research, offline only. No vehicle, ADB, installation, Binder invocation, or display-control operation was performed. `safeForHonda() == false`.

## Verdict

**NO_SUPPORTED_PATH_FOUND_IN_REVIEWED_SCOPE.** Reviewed manifests, factory display Binder/JAR interfaces, host lifecycle reports, HondaHack analysis, and prior captures establish a private in-process View insertion path, but no supported caller-facing Bitmap, Surface, buffer, frame, or View admission contract for an independent navigation producer. Technical reachability does not confer authorization.

The current API-17 `PaneLease` is a synthetic host contract comparison. Its bounded frames, ownership, revocation, warning withdrawal, and restoration rules are useful requirements; passing its tests does not establish Honda admission or runtime behavior.

## Evidence status and existing research

This report uses the published PR #80 Navigation-pane contract/observation plan, PR #65 CL-HH-06A/B research, PR #67 CL-HH-07, PR #66 CL-SYS-01A, PR #68 CL-IF-01, and CL-R10B ownership findings. PR #80's static trace already answers who selects the host page and how the host acknowledges it; this report does not repeat those traces.

Existing private recording summaries establish that HondaHack's private casting path has appeared on the physical cluster and that one Door Open case preempted and restored it. The audited CL-R10B report notes the original footage is not present in its audited tree. Those records do not show synchronized Navigation page exit/re-entry, complete Stop Casting restoration, all warning classes, or a calibrated physical aperture. See published [CL-R10B display ownership report](https://github.com/bmreyes25/ClarityLink/blob/feature/cl-hh-03-view-observability/research/hondahack/cl-r10b-display-ownership.md) and PR #80's [Navigation-pane contract](https://github.com/bmreyes25/ClarityLink/blob/claude/cl-honda-111-01-factory-receiver/research/honda/cl-honda-111-01-navigation-pane-contract.md). These references summarize evidence; they do not make the private route supported.

### Historical factory and HondaHack observations

The preserved CL-HH-06 session summary records a factory Navigation Display 1 image (compass/grid and Menu) while the physical cluster photo also shows fixed gauges/indicators; it records casting off/on and a center Maps-to-Music switch, with Screen Casting mirroring those center-display states. The Screen Casting Display 1 image includes factory cluster settings/Menu over a black remainder. Advanced Meter changes Display 1 to compass/vehicle-data widgets through the same private injected host infrastructure, while its named activity window remains on Display 0. A separate historical Test 4C Door Open clip reports one preemption and return. These are distinct observations and do not establish an external app interface, page exit/re-entry behavior, complete stop-cast restoration, universal warning priority, or an OEM aperture. See PR #65's [CL-HH-06 display path](https://github.com/bmreyes25/ClarityLink/blob/research/cl-hh-06a-apk-inventory/research/hondahack/hondahack-display-path.md), [CL-HH-06B data flow](https://github.com/bmreyes25/ClarityLink/blob/research/cl-hh-06a-apk-inventory/research/hondahack/cl-hh-06b-display1-data-flow.md), and [September 25 session summary](https://github.com/bmreyes25/ClarityLink/blob/research/cl-hh-06a-apk-inventory/research/REPORT.md). The CL-HH-07 review separately distinguishes the pixel-copy path from semantic/widget rendering and notes abnormal lifecycle recovery remains unknown.

## Findings by question

### A. Frame admission

No supported external producer contract was found in reviewed scope. `ExternalDisplayApService` exposes status, interrupt, channel/info, meter, callback and diagnostic operations using structured scalar/control objects. The inspected Binder schema has no `Bitmap`, `Surface`, `SurfaceTexture`, pixel buffer, encoded frame, stream descriptor, or View handoff. `ExternalDisplayOutService` owns the Android roots; its exported service's `onBind()` returns null. Its `InterfaceWindow` root access and `addView` methods are in-process implementation details.

Android API-17 `Presentation` and display contexts are generic Android capabilities, not Honda approval or proof that an ordinary app can add a window on this display. A successful window add, if ever observed, would still not define ownership, safe geometry, warning order, or restoration.

### B. Host ownership

`ExternalDisplayOutService` owns content attachment and its WindowManager roots on logical Display 1. It builds/tears down its own bottom, main, and interrupt roots with service/display lifecycle. The cluster controller selects a page and reports the selection/status to the host. For host-rendered pages, the host reports waiting, constructs or resumes its content, then reports displaying; it reports none for meter-native pages. On page selection change the host resumes an existing screen or clears its own screens before constructing another. The static evidence does not establish what an unsupported injected child does when the host clears/replaces its screens.

### C. Read-only page observation

Offline static evidence identifies a steering-switch status record delivered to the host with selected contents ID, interrupt status/info and custom-guidance state. That record is the host's page-state input. No reviewed caller-facing read API for an external ordinary app was established. Observing the factory UI with a camera is passive; reading the private/control Binder would not be justified by its existence, and invoking its control methods is outside scope.

### D. Warning precedence

The host has a separate interrupt root, attached after the main root, and receives interrupt/status callbacks through the AP/control service. This proves the factory Android root arrangement in the audited code, not downstream cluster compositing or guaranteed preemption for external windows. One Door Open recording demonstrates only that one case. HondaHack visibility follows reported content/status, but a missing callback or `none` state can leave its prior visibility unchanged. No custom pane can currently be guaranteed to withdraw before every factory warning.

### E. Geometry

| Coordinate system | Evidence | Meaning and limit |
|---|---|---|
| Logical Display 1 | 800×480 | Honda/Android HDMI canvas observed in preserved evidence; not the physical cluster aperture. |
| Factory full-window roots | Display 1-sized WindowManager roots | Android host composition area; downstream mask/crop/transform remains unknown. |
| HondaHack layout-local region | 584×191 | App/layout-local placement region, not an OEM Navigation SafeArea. |
| Physical visible Navigation aperture | Unknown | Requires calibrated external observation correlated with known visible content; camera pixels still do not define an OEM-authoritative SafeArea. |
| CarPlay SafeArea | Not established for the Honda physical cluster | Requires an authoritative receiver/OEM contract; cannot be inferred from Display 1 or a camera measurement. |

### F. Lifecycle and restoration

| Event | Established | Unknown / assumed only |
|---|---|---|
| Page loss/change | Host receives selection status and resumes existing host screen or clears its own screens before replacement. | Whether a private injected view is detached/hidden on every transition; whether an unsupported custom frame is withdrawn. |
| Host stop/restart | Host removes its own roots; HondaHack's HMI stop path removes/recreates its injected view on lifecycle broadcasts. | Independent producer behavior after missed broadcast, abrupt process death, or partial host restart. |
| Display removal/reconnection | Host tears down on removal and rebuilds when the display is valid again, according to static lifecycle research. | Whether injected content is recreated safely and only for the current Navigation generation; no supported third-party lifecycle contract. |
| Existing Stop Casting | HondaHack clears its casting flag and refreshes its layout; the view remains attached and can show its alternate layout. | This is not full detachment or proof of factory restoration. Runtime physical outcome after stop is not established by static code. |
| Warning/interrupt | Separate interrupt root attaches after main; one Door Open example preempted/restored. | Universal warning priority, physical z-order, time-to-withdraw, and all warning/interrupt cases. |

## Interface and authorization matrix

| Interface role | Owner | Caller authorization evidence | Input/output type | Behavior class | Known side effects | Lifecycle contract | Evidence source | Supported for external apps? |
|---|---|---|---|---|---|---|---|---|
| `ExternalDisplayOutService` renderer and `InterfaceWindow` | Honda external-display process | Exported declaration is present; `onBind()` returns null. Root methods are static/in-process. Manifest requests system-window permissions; effective grants are not established for a third party. | Internal Android Views and WindowManager roots; no cross-process frame argument. | Mixed/internal renderer | Attaches/removes Honda windows and content. | Host owns its roots; display/service teardown and rebuild are described statically. | PR #65/CL-R10B; PR #80 Navigation-pane contract. | **No supported external frame/View endpoint found.** |
| `ExternalDisplayApService` Binder/JAR | Honda AP/control service | Exported; no component-level bind permission in reviewed manifest. Method checks and successful caller access remain unknown. Manifest requests `VEHICLE_RW`. | Integer/boolean/string/Honda parcelable status, interrupt, channel/info, meter/control, callback and diagnostics. | Mixed/control-capable | Can report/control LVDS, meter, interrupt, channel and Honda service state. Exact effects are operation-specific; no calls made. | Callback and status relationships exist; no external frame lease/withdraw contract. | PR #65 API surface; permission/signing audit in CL-HH-06A. | **No for frame admission;** exported does not mean authorized or safe. |
| CPU-communication / cluster page-status path | Honda cluster/controller and AP-service transport; cluster arbitration is beyond reviewed host | No ordinary-app caller contract. Host consumes status; request/notify operations are not a read-only external observer API. | Structured page contents ID, status, interrupt and control messages. | Mixed/control-capable | Page request/notifications traverse a service adjacent to vehicle communication; exact bus effects are not generalized. | Host waiting/displaying/none handshake; controller-side use is not documented in reviewed set. | PR #80 bounded static host trace and interface description. | **No external read or display-control authorization established.** |
| Factory Navigation/TBT service | Honda Navigation service | Permission and effect boundaries vary; `VEHICLE_RW`/`ACCESS_MAP` are not proven available to ordinary apps. | Semantic route/guidance objects and callbacks. | Mixed/control-capable | Can affect factory navigation state; some audited guidance paths may reach B-CAN. | No external pixel-frame or display restoration contract. | CL-SYS-01A and CL-R10B static review. | **Not a frame sink; external use not established.** |
| Android API-17 `Presentation` / display context | Android app WindowManager plus Honda display policy | Generic API exists. Honda admission, app identity/signature, policy and z-order remain unknown. | App-owned View/window on a Display. | Control-capable UI operation | Adds an app window; potential overlap/occlusion. | AOSP responds to display removal; no Honda warning/page/restore guarantee. | API-17 static review in CL-HH-06A; AOSP evidence. | **Generic Android supported; Honda Display 1 contract not established.** |
| HondaHack Xposed View insertion | HondaHack injected into Honda host process | Requires private in-process execution/rooted or injected environment; not an OEM caller permission. | Bitmap captured from Display 0 and private View content inserted into Honda roots. | Control-capable/private | Changes Honda-owned view composition; other HondaHack modules may use unrelated interfaces. | Stop Casting keeps the View attached; HMI lifecycle handling is partial. | CL-HH-06A/B and CL-R10B private static analysis; summarized publicly. | **No. Private technique, not supported for external apps.** |
| Synthetic API17 `PaneLease` | ClarityLink laboratory host | Synthetic token/lease model only. | Bounded frame messages and lease state. | Model/control-capable | Synthetic host owns output, can withdraw/recover. | Explicit expiration, warning withdrawal and restoration assumptions are testable in the lab. | Current synthetic API17 implementation/tests; model evidence only. | **Not a Honda interface.** |

## Observation decisions

### Q1 — Navigation selection and restoration: passive camera is justified

The existing one-warning footage and static host trace leave page exit/re-entry and physical Stop Casting outcome unanswered. A single owner-approved, parked, fixed-camera session using only the pre-existing casting UI can determine whether casting follows Navigation page selection and whether the physical factory Navigation appearance returns after Stop Casting. This changes the synthetic visibility/restoration assumptions and whether any later design needs an explicit independently authorized revoke path. It cannot establish a supported API.

### Q2 — Page/status logs over ADB: not justified on reviewed evidence

The reviewed reports identify the status record and host handshake but do not identify a preserved, narrowly attributable log tag or log statement for page transitions. The actual exact-tag search has not been closed against a complete code-level log-call inventory in this public-safe research set. Therefore no ADB target command, tag, or expected record can be specified honestly, and an unfiltered capture would violate the narrow collection requirement. Reconsider only if a separate offline source review identifies an exact page/interrupt/status tag and proves it is emitted by the matching build. Even then, passive ADB would observe a record only; it cannot authorize an undocumented frame-admission API.

### Q3 — Physical Navigation geometry: one passive calibrated sample is justified with Q1

The existing logical resolution and HondaHack local layout do not establish the physical aperture. If the existing casting path can show a known, uniquely marked pattern without altering software, a single square-on external-camera image/short clip with a rigid scale reference can estimate the visible crop/transform for that specific state. This can replace an uncalibrated geometry assumption with a measured sample, but does not create an OEM SafeArea or general guarantee. If no known pattern is already available through the existing UI, omit geometry rather than introduce new content or controls.

## Remaining blockers

An OEM-documented, caller-authorized frame source/surface contract; exact app/signature/permission rules; display and Navigation ownership/lease semantics; authoritative physical viewport/SafeArea; host-controlled warning preemption and immediate withdrawal; stale-frame and generation behavior; host/service/display loss recovery; factory restoration; and a reviewed boundary proving any supported admission/release operation's side effects. A camera observation can reduce page behavior and geometry unknowns only. ADB does not close any of these authorization gates.
