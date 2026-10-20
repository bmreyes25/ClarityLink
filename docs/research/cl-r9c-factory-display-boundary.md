# CL-R9C — factory Navigation and Display 1 frame boundary

**Result:** no supported Honda frame-admission interface was established. The observed Honda output path is factory-owned Android Views in `ExternalDisplayOutService`, through a full-frame Display 1 HDMI output. The evidence does not expose an independently authorized frame input. The Honda display gate remains disabled and `safeForHonda()` remains false.

This report uses the existing sanitized static and read-only evidence notes listed below. It does not repeat firmware extraction or include private firmware, captures, credentials, or device identifiers. No Honda, vehicle, ADB, iPhone, APK-install, framebuffer, or display-takeover operation was performed for this work. Honda conclusions are limited to the reviewed component/interface inventory and the previously recorded read-only display observations; they do not imply a supported OEM API.

## Factory rendering path

```text
Factory navigation / route state
  ├─ Navigation APIs carry semantic NavGuide / NavCurrent / display-demand data
  │    (not a bitmap, Surface, or decoded-video frame)
  └─ Honda ExternalDisplayOutService consumes callbacks and selects Honda Views
       └─ ContentsManager / InterfaceWindow attaches Views to Honda-owned roots
            ├─ bottom root
            ├─ main root (Navigation/TBT and other ordinary pages)
            └─ interrupt root (interrupt content; warning precedence not proven)
                 WindowManager display-context windows, full-frame 800×480
                    └─ Android Display 1 / HDMI, layer stack 1
                         SurfaceFlinger / HWC full-frame output (last verified
                         logical stage; physical cluster transform/composition unknown)
                            └─ visible cluster pixels (observed correspondence,
                                downstream crop/mask and exact destination unknown)
```

The saved static audit identifies `ExternalDisplayOutService` as the renderer/window owner: it creates a display context, attaches bottom/main/interrupt roots, and inserts Honda content Views. Honda Navigation libraries supply semantic route and TBT state; the audited interfaces do not supply arbitrary decoded frames. The service selects the last item returned by `DisplayManager.getDisplays()` in the reviewed implementation. That implementation detail is not a documented Display 1 selector or third-party extension contract.

Saved SurfaceFlinger/display observations identify Display 1 as an 800×480 HDMI logical display with layer stack 1 and full-frame source/destination rectangles. A paired factory-navigation screen and cluster observation shows corresponding navigation content, while other cluster indicators are absent from the Android capture. Thus the HDMI output is a verified logical stage in the visible path; it is not a complete capture of physical cluster composition. No OEM navigation viewport, physical mask, scaling transform, or safe area is established.

Navigation page selection appears to be mediated by Honda's cluster controls and ExternalDisplay UI/control callbacks, but the reviewed notes do not isolate a single authoritative “select Navigation page” operation and its inverse. Similarly, `InterfaceWindow` has separate main and interrupt roots and the host removes its roots with its own window lifecycle, but this does not establish warning precedence or a safe per-page hide/restore contract. Treat those as unknowns.

## Answers to the rendering questions

| Question | Finding | Classification |
|---|---|---|
| A. Component generating navigation frames | Honda `ExternalDisplayOutService` produces Android View content for its roots. Navigation APIs provide semantic route/TBT state upstream. No independent decoded-frame producer is identified. | `STATIC_HONDA_EVIDENCE` |
| B. Presentation owner | `ExternalDisplayOutService` owns the display-context `WindowManager` roots and inserts Honda content Views. | `STATIC_HONDA_EVIDENCE` |
| C. Composition mechanism | The evidenced path is Android Views/window roots through WindowManager/SurfaceFlinger to Display 1. No Honda Navigation `SurfaceTexture`, shared-frame IPC, H.264 consumer, or native decoder-to-window connection was found in the audited display path. | `STATIC_HONDA_EVIDENCE`; downstream details `UNKNOWN` |
| D. Display 1 selection | The audited service enumerates displays and selects the last returned display before creating a display context. This is observed implementation behavior, not a public selector contract. | `STATIC_HONDA_EVIDENCE` |
| E. Final output owner | Honda owns the Android roots; SurfaceFlinger/HWC emits the observed full-frame HDMI Display 1 output. The next physical cluster compositor/mask is not identified. | Android ownership `STATIC_HONDA_EVIDENCE`; physical stage `UNKNOWN` |
| F. Factory Navigation selection | Factory cluster selection and Honda Navigation/display callbacks select factory content. The exact owning control operation and a third-party selection API are not established. | `INFERRED` / `UNKNOWN` |
| G. Coexisting visual layers | Bottom, main, and interrupt roots coexist in the host; separate physical cluster indicators are absent from the Display 1 capture. | Roots `STATIC_HONDA_EVIDENCE`; physical layering `UNKNOWN` |
| H. Warning precedence | The host has an interrupt root, but relative z-order, downstream warning priority, and protected warning regions are unproven. No single precedence controller is established. | `UNKNOWN` |
| I. Hide and restore | Host/service window lifecycle removes its roots. Factory page-level hide/restore, app-window dismissal, and restoration of a displaced factory page are not documented for an external frame consumer. | `STATIC_HONDA_EVIDENCE` for host-root lifecycle; otherwise `UNKNOWN` |
| J. Legal geometry | No public/OEM interface determining an external frame's legal placement was found. Factory layouts govern Honda's own Views; that is not permission for an external renderer. | `UNKNOWN` |
| K. Navigation safe area | Unknown. 800×480 is the logical HDMI canvas, not the physical Navigation rectangle. | `STATIC_HONDA_EVIDENCE` for logical size; safe area `UNKNOWN` |
| L. Supported external consumer | No supported external View/Surface/Bitmap/H.264/frame endpoint was found. | `STATIC_HONDA_EVIDENCE` for audited interface absence; future OEM API `UNKNOWN` |

## Candidate boundary review

| Candidate | Evidence / owner | Input and authorization | Geometry, lifetime, warnings, restoration | Decision |
|---|---|---|---|---|
| `ExternalDisplayOutService` / `InterfaceWindow` | Honda-owned view host; service is exported, but its `onBind()` returns null. Root access and `addView` are same-process methods. | Regular Android `View`; caller must already execute in the host process. No external caller authorization contract for frame submission was found. | Roots are full-frame on Display 1. Physical Navigation inset is unknown. Main/interrupt roots exist, but precedence and a supported caller's teardown/restoration are unspecified. | Internal render implementation, not a supported external admission API. Do not use Xposed or service replacement as a substitute. |
| `ExternalDisplayApService` Binder | Honda service/control contract in the audited library interface. | Meter, channel, LVDS, interrupt, status, and callback/control values; no `Surface`, `Bitmap`, pixel buffer, H.264, stream FD/socket, or decoded frame argument. Runtime caller/method authorization is not inferred from `exported`. | No geometry or frame lifetime contract. Warning/control notifications do not grant rendering ownership. | Reject as a pixel output boundary. |
| Navigation / HondaNavigation APIs | Honda semantic guidance services and callbacks. | Route/TBT objects and display demand; permissions and effect of any setter are distinct from pixel submission. | No frame geometry. A semantic call could affect factory navigation state; no external presentation lifecycle or restore semantics are documented. | Not a decoded-frame sink. Do not use to inject pixel content. |
| Android API-17 `Presentation` / display context | General AOSP API documentation, not Honda admission evidence. | Generic app can request a window on an enumerated display; Honda's display policy, app grant/signing, and `show()` acceptance are unverified. | AOSP logical display dimensions are available; Honda physical safe area, z-order, warnings, service coexistence and factory restore are unknown. | Candidate for a separately authorized evidence review only; not an established Honda interface. |
| HondaHack screen-cast/Xposed path | Existing third-party static analysis plus earlier read-only output observation. It captures Display 0 to a bitmap and injects a View into Honda's host process. | Bitmap/View through third-party code and Xposed host-process execution, not a Honda OEM consumer contract. | Its layout dimensions are local to that injected view, not the factory Navigation area. Warning precedence and safe restoration remain unknown. | Demonstrates private in-process composition only. Unsupported for ClarityLink. |
| `disp_com_meter` / cluster utilities | Preserved notes identify command/control messaging and cluster utility wrappers. | Commands/control values, not an identified RGB/video/frame submission API. | No pixels, safe-area data, warning compositor, or external app lifetime contract. | Not an output boundary. |

No reviewed candidate meets all four admission requirements: an OEM-documented frame sink, caller authorization, bounded frame/geometry schema, and owner-defined withdrawal/restoration behavior.

The decisive distinction is: Honda has an observed non-public internal View insertion path; no supported public/OEM frame-admission API is established; and no Honda secondary decoded-frame admission contract is known from the reviewed evidence.

## Audi comparison (reference only)

Read-only inspection of the upstream files listed below found a managed QNX Screen window in `common/cluster_surface.c`: it creates a Screen application context/window, sets window properties, calls `screen_manage_window`, creates buffers, detects invalidation/disown, and recreates or destroys the window. `AltScreenModule` owns the Audi cluster context transitions: its single worker selects Audi-specific cluster contexts after video readiness/navigation state and returns the cluster to its stock context on stop. `DisplayManagerMIB2High` defines displayable composition for those contexts and arbitrates context switching/KDK visibility. The source comments also document view-area selection and context behavior.

These are Audi implementation details on QNX with an Audi-modified DisplayManager, managed Screen windows, displayable/context IDs, and an AltScreen video path. Honda uses Android Views and WindowManager roots on HDMI Display 1 plus a separately unresolved downstream cluster stage. The Audi context identifiers, Screen properties, displayable constants, call sequence, and QNX hooks are not portable Honda interfaces. No Audi source code is copied here. The upstream repository is GPL-3.0; this report uses only independently written descriptions of observed behavior.

| Audi source / symbols | Observed Audi behavior | Honda correspondence and consequence |
|---|---|---|
| `common/cluster_surface.c`: `cluster_surface_create`, `cs_open_window`, `cluster_surface_lost`, `cluster_surface_recreate`, `cluster_surface_destroy` | Managed QNX Screen application window; configured dimensions/buffers; detects loss/disown and recreates with backoff. | Honda's static Android root owner is not a QNX Screen managed window. No supported frame-admission API is inferred. |
| `java_patch/com/luka/carplay/core/AltScreenModule.java`: `start`, `stop`, `setNavActive`, `switchLoop`, `applySwitch` | A serialized worker selects the Audi cluster map/navigation composition after renderer readiness; stop requests stock context restoration. Navigation activation and renderer readiness are independent gates. | Honda has no corresponding documented external owner/context-switch contract. Generic lifecycle ideas do not establish Honda warning/restore behavior. |
| `java_patch/de/audi/tghu/fwhmi/DisplayManagerMIB2High.java`: `defineContexts`, `configureDM`, `setKDKVisible`, `switchContext` | Audi-specific displayable lists form contexts; stock context writes and KDK overlays are managed while its CarPlay contexts are active. | Honda's Android roots and any downstream cluster content have different owners and composition. Do not reuse Audi context/displayable IDs or takeover semantics. |

The Audi repository's higher-level reports include author-reported iOS reverse-engineering and platform-specific observations. Those are not protocol guarantees for all iPhones and are not evidence about Honda. This comparison is architectural prior art only.

## Evidence matrix

Classifications are deliberately source-scoped: `STATIC_HONDA_EVIDENCE` means preserved Honda static-audit conclusions; it is not an OEM support statement. `VERIFIED_HONDA_CONTRACT` is not assigned to any frame-admission path.

| Subject | Audi source / symbol | Observed Audi behavior | Honda evidence reference | Honda finding | Classification | Missing proof | Compatibility consequence |
|---|---|---|---|---|---|---|---|
| Factory pixel producer | `AltScreenModule.start` / renderer readiness; `cluster_surface_create` | Audi has an explicit separate video renderer and managed cluster output surface. | `research/runtime/43t1-r4c-honda-display1-ownership-audit.md`; `research/display/externaldisplay-host-flow.md` | Honda display service creates View content; Navigation APIs are semantic. No decoded Type111-to-View producer seam is shown. | `STATIC_HONDA_EVIDENCE`; Audi `AUDI_REFERENCE_ONLY` | OEM frame source/sink contract. | A decoder cannot be assumed to submit frames to factory Navigation. |
| Display target and ownership | `DisplayManagerMIB2High.defineContexts` / `switchContext` | Audi DisplayManager explicitly composes and selects named cluster contexts. | `research/runtime/43t1-r4c-honda-display1-ownership-audit.md`; `research/navigation-safe-area.md` | Honda ExternalDisplay service owns Android roots targeting Display 1; final physical compositor unknown. | `STATIC_HONDA_EVIDENCE`; Audi `AUDI_REFERENCE_ONLY` | Honda-owned display admission and output-layer ownership spec. | Do not take over or guess a context/window. |
| External content API | `cluster_surface_create` managed Screen window | Audi native output is created/managed through QNX Screen. | `research/display/externaldisplay-api-surface.md` | ExternalDisplayOutService `onBind()` null; AP Binder has control/status arguments, no frame sink. | `STATIC_HONDA_EVIDENCE` | Published Honda cross-process endpoint, auth, input schema. | Exported service declarations are not frame permissions. |
| Display geometry | `DisplayManagerMIB2High.configureDM` / Audi-specific composition | Audi source configures its renderer/displayables for Audi hardware. | `research/navigation-safe-area.md`; `research/runtime/43t1-r4a-cluster-rendering-architecture.md` | Android canvas is 800×480; physical Navigation rectangle/mask/transform unknown. | `STATIC_HONDA_EVIDENCE` for canvas; `UNKNOWN` safe area; Audi `AUDI_REFERENCE_ONLY` | OEM viewport and legal content region. | No test or frame may be represented as physically safe. |
| Warning precedence | `AltScreenModule.applySwitch`; `DisplayManagerMIB2High.setKDKVisible` | Audi coordinates map context and KDK displayables in its own manager. | `research/runtime/43t1-r4d-warning-zorder-static-evidence.md` | Honda has an interrupt root, but relative warning order and downstream priority are not proven. | `STATIC_HONDA_EVIDENCE` for root existence; `UNKNOWN` precedence; Audi `AUDI_REFERENCE_ONLY` | OEM warning preemption/withdrawal contract. | Keep Honda output disabled. |
| Factory navigation selection | `AltScreenModule.setNavActive` / `setViewAreaMode` | Audi module consumes navigation and view-area state to change context/presentation. | `research/runtime/43t1-r4c-honda-display1-ownership-audit.md`; `research/navigation-safe-area.md` | Honda semantic navigation callbacks are present, but exact page-selection owner/API and external selection semantics are not established. | `STATIC_HONDA_EVIDENCE` for callbacks; `INFERRED` selection; `UNKNOWN` external contract | Honda-owned selection, hide/restore lifecycle documentation. | Don't invoke navigation setters as pixels or treat status as authorization. |
| Service lifecycle and restoration | `AltScreenModule.stop` / `applySwitch`; `cluster_surface_destroy` | Audi explicitly restores stock context and releases its renderer window. | `research/display/externaldisplay-host-flow.md`; `research/runtime/43t1-r4d-warning-zorder-static-evidence.md` | Honda removes its own roots with service lifecycle; external-view cleanup and restoration contract absent. | `STATIC_HONDA_EVIDENCE` for host lifecycle; `UNKNOWN` external restoration; Audi `AUDI_REFERENCE_ONLY` | OEM-defined consumer withdrawal, owner-loss, factory restore. | No safe external teardown behavior can be assumed. |
| Independent API-17 app | Not applicable | Audi code is privileged platform-specific implementation. | `research/runtime/43t1-r4c-api17-external-display-static-review.md`; `research/runtime/43t1-r4c-independent-display-app-feasibility-gate.md` | AOSP `Presentation` exists; Honda normal-app window admission and safe ordering are unknown. | `AUDI_REFERENCE_ONLY` / `UNKNOWN` | Honda admission, signer/permission, warning and physical-output evidence. | A generic Android API is not Honda authorization. |
| Screen casting | Audi renderer receives a separately negotiated CarPlay screen stream. | Audi-specific stream and output are integrated. | `research/hondahack/hondahack-display-path.md` (sanitized findings only) | Prior HondaHack path uses private Xposed host-process View insertion; not a supported API. | `STATIC_HONDA_EVIDENCE` for observed private path; not a contract | OEM-authorized consumer or documented app entry. | Do not reuse HondaHack/Xposed or its geometry. |

## Offline contract gate and regression coverage

No supported Honda boundary was found, so this change adds no Honda rendering adapter. `HondaDisplayBoundaryGate` is a diagnostic status gate only; it is not wired into a production display pipeline and does not enforce output ownership. It has no evidence/token override and always raises `EvidenceRequired` when asked to authorize Honda output. Existing CL-R6 lab output remains the only output host used by the laboratory.

The missing-evidence codes separately name frame admission, caller authorization, accepted frame schema, display ownership, geometry/safe area, warning precedence/withdrawal, view replacement, parent teardown/authority loss, and factory restoration. This list is not a proposed Honda API and cannot authorize an output.

CL-R6/CL-R7 regression coverage remains synthetic/lab-only. The focused suite exercises session admission, frame bounds/generation, stale-frame rejection, warning withdrawal/recovery, output ownership, view replacement, parent teardown, factory restoration, and refusal to draw after authority loss. Passing those checks validates the lab host, not Honda output or safety.

## Decisive status and exact evidence gap

- **Verified output ownership:** Honda's ExternalDisplay service owns the Android View roots, and the saved logical output ends at Display 1 HDMI/SurfaceFlinger full-frame composition.
- **Observed internal rendering:** Honda Navigation/TBT is represented as Honda-owned Views on that path. A third-party Xposed route can insert views in the host process, but is private and unsupported.
- **Supported public/OEM interface:** none found for independently decoded frames.
- **Unsupported private behavior:** Xposed injection into the Honda host and any service replacement, privileged overlay, framebuffer write, or undocumented native/Binder path.
- **Unknown safety behavior:** physical map rectangle/crop, warning precedence, external-app z-order, owner-loss behavior, and factory restoration.

The narrowest missing interface is an **OEM-documented, caller-authorized frame-admission endpoint owned by the Display 1 presentation authority**. Its specification must define the accepted frame/surface type and pixel geometry, the caller identity/permission, who owns and may replace the output layer, generation/session scoping, warning preemption and frame withdrawal, host/display removal, and guaranteed factory Navigation restoration. A supported normal-app `Presentation` admission with documented warning/safe-area/lifecycle behavior could be an alternate interface, but no Honda evidence currently establishes that contract.

The next evidence needed is the Honda/OEM interface specification or a Honda-provided supported application sample/API plus its authorization and lifecycle contract. If no such API exists, an explicitly authorized OEM extension specification is required. Another screenshot, string match, service export flag, generic Android API, or private Xposed demonstration cannot close this gap.

## Evidence sources

Local preserved summary notes:

- `research/runtime/43t1-r4a-cluster-rendering-architecture.md`
- `research/runtime/43t1-r4c-honda-display1-ownership-audit.md`
- `research/runtime/43t1-r4c-api17-external-display-static-review.md`
- `research/runtime/43t1-r4c-independent-display-app-feasibility-gate.md`
- `research/runtime/43t1-r4d-warning-zorder-static-evidence.md`
- `research/runtime/43t1-r4d-app-window-admission-matrix.md`
- `research/display/externaldisplay-api-surface.md`
- `research/display/externaldisplay-host-flow.md`
- `research/hondahack/hondahack-display-path.md`
- `research/navigation-safe-area.md`
- `research/runtime/r5y-display-sink-contract.md`
- `research/runtime/r7c-display1-presentation-adapter.md`
- `research/runtime/r7c-honda-adapter-readiness.md`

Audi source references inspected for comparison (upstream repository, GPL-3.0; no code copied):

- [`common/cluster_surface.c`](https://github.com/luka-dev/mib2q-carplay-rgi/blob/main/common/cluster_surface.c)
- [`AltScreenModule.java`](https://github.com/luka-dev/mib2q-carplay-rgi/blob/main/java_patch/com/luka/carplay/core/AltScreenModule.java)
- [`DisplayManagerMIB2High.java`](https://github.com/luka-dev/mib2q-carplay-rgi/blob/main/java_patch/de/audi/tghu/fwhmi/DisplayManagerMIB2High.java)
- [Upstream repository license and project context](https://github.com/luka-dev/mib2q-carplay-rgi)
