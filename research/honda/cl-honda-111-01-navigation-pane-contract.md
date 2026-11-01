# CL-HONDA-111-01 / M4 — Navigation-pane contract and HondaHack cluster-casting architecture

Offline, static, synthetic. `safeForHonda() == false`. Evidence labels as in the [evidence map](cl-honda-111-01-evidence-map.md). Honda numeric identifiers, class and method names, and decompiled bodies stay in private storage; this document is role-level. Nothing here installs, runs or hooks anything, and nothing authorizes a Honda display operation.

## 1. Four layers that must not be confused

```
 ┌───────────────────────────────────────────────────────────────────────────────┐
 │ L0  Physical cluster panel + gauges      downstream composition, mask, crop    │
 │       aperture / transform: UNKNOWN (Display 1 capture lacks physical          │
 │       indicators; no calibrated mapping)                                       │
 ├───────────────────────────────────────────────────────────────────────────────┤
 │ L1  Android logical Display 1            800×480, observed (not created) by    │
 │       the Honda host; removal tears the host down, return rebuilds only if     │
 │       the display is valid                                    HONDA_STATIC     │
 ├───────────────────────────────────────────────────────────────────────────────┤
 │ L2  Honda host windows (Android)         bottom → main → interrupt, all        │
 │       full-frame; interrupt attached last (top-most), hidden by default;       │
 │       interrupt visibility toggles independently          HONDA_STATIC         │
 ├───────────────────────────────────────────────────────────────────────────────┤
 │ L3  Selectable pages (driver-visible)    the cluster's pages are addressed by  │
 │       a numeric display-contents identifier plus a status, reported by the     │
 │       host's content manager. "Navigation" is one value; "warning" is another  │
 │       value in the same scheme AND there is a separate interrupt window.       │
 │       Who decides the selection: NOT established            HONDA_STATIC/UNKNOWN│
 ├───────────────────────────────────────────────────────────────────────────────┤
 │ L4  Content inside a window root         factory turn-by-turn Views, a         │
 │       third-party injected View (HondaHack), or a future ClarityLink pane      │
 ├───────────────────────────────────────────────────────────────────────────────┤
 │ L5  Viewport inside the visible area     explicit destination rectangle.       │
 │       Physical safe area: UNKNOWN. HondaHack's 584×191 is layout-local only.   │
 └───────────────────────────────────────────────────────────────────────────────┘
```

Drawing to L1 is **not** drawing inside the Navigation page (L3). Being a child of a main-layer root (L2) says nothing about which L3 page is showing, whether L0 will show it, or what the viewport (L5) is. A pane contract has to track all of them, which is what `navigation_pane_host.py` does for the synthetic case.

## 2. The brief's ten placement questions

| # | Question | Answer | Class |
|---|---|---|---|
| 1 | How does the cluster choose the Navigation page? | The head-unit host addresses pages by a numeric contents identifier and a status. It **requests** a page by sending an interrupt notification with that identifier, and **reports** what it is displaying with a status notification; both go from the host, through the ExternalDisplay AP service, to a **CPU-communication service**. The decision is therefore arbitrated on the far side of that service (the meter/cluster controller), and the Java host mirrors the result. | `HONDA_STATIC_CONFIRMED` (call chain, from the preserved Honda services) / arbitration location `INFERRED` |
| 2 | Which Honda service or model owns that choice? | The CPU-communication service is the transport; the cluster-side controller is the likely arbiter but is not in the preserved set. The ExternalDisplay Out service holds the content manager that renders pages and the AP service forwards display status, interrupt and operation notifications. That same CPU-communication interface also carries B-CAN channel data and cooperation messages, so a page request is **adjacent to a vehicle-bus path**; its exact vehicle-side effect is not established. | `HONDA_STATIC_CONFIRMED` (interfaces) / effect `UNKNOWN` |
| 3 | Is factory Navigation content created only for that page? | The host has per-content modules (turn-by-turn, audio, phone, and others) and a "top view" identifier. Whether the Navigation module's Views exist only while that page is selected is not shown. | `UNKNOWN` |
| 4 | Does HondaHack's content follow page visibility? | **Yes by construction of its code.** Its view's visibility is a function of the host's reported (contents id, status): visible while the reported content is one of two identifiers it uses and the status is active; hidden when a different content is active; unchanged when the status is "none". One of those identifiers is a **different-purpose slot it requests for itself**. | `HONDAHACK_STATIC` (private decompile, this campaign) |
| 5 | Which root does HondaHack use? | It asks for the **interrupt layout** first; if that layout is visible it uses the interrupt layout's root, otherwise the **main layout's** root. It adds its view at index 0, and when visible calls bring-child-to-front on that root, then bring-to-front on the root itself. | `HONDAHACK_STATIC` (control flow from the preserved decompile; the two getters' identities from the external string decode, C1) |
| 6 | Main or interrupt hierarchy under different states? | Both, by the rule above. In a normal state with no interrupt showing: the main root. While an interrupt layout is visible: the interrupt root, but gated invisible unless the reported content is one of its two identifiers. | `HONDAHACK_STATIC` |
| 7 | Does warning content stay independent and top-most? | Statically the factory attaches the interrupt window last. HondaHack's view is hidden whenever the reported content is a different, active one, which includes a warning content. That is a *callback-following courtesy*, not a precedence guarantee: it fails open to the previous visibility if a callback is missed or reports "none". | `HONDA_STATIC_CONFIRMED` / `HONDAHACK_STATIC` / precedence `UNPROVEN` |
| 8 | What do display removal and restoration do to injected content? | The factory host tears down and rebuilds its own stack. HondaHack's view is removed when the HMI service stop is broadcast and recreated on start/restart; behaviour across a bare display-link drop is not shown. | `HONDAHACK_STATIC` (partial) / `UNKNOWN` |
| 9 | How does factory Navigation resume after custom content disappears? | HondaHack's **Stop Casting does not detach the view**. It clears a flag and refreshes the layout, which flips visibility between its meter layout and its cast layout by preference. The view stays attached and a newly arriving frame restarts casting. Restoration of factory content is whatever the host shows beneath. | `HONDAHACK_STATIC` (resolves part of the earlier U-20) |
| 10 | Is a supported, permission-checked original renderer host identifiable? | No. The host exposes no frame endpoint; access is process-local; the exported display-control Binder carries control and status, not pixels; HondaHack reaches the host by running inside it. | `UNSUPPORTED` in reviewed evidence |

## 2a. P1 result: who selects the page, and what gates physical visibility

A bounded static trace of the host's content manager (preserved Honda services, read-only, offline) resolved the main "who decides" question for the Java side.

1. **The cluster controller selects; the host follows.** The host receives a *steering-switch status* record carrying the selected contents identifier, an interrupt status, interrupt info and a custom-guidance flag. That record is the host's only input to "which page is showing". It originates on the CPU-communication side, so the driver's steering-wheel page selection is arbitrated there and delivered to the host. (`HONDA_STATIC_CONFIRMED`)
2. **Two kinds of page.** Identifiers in the meter range are rendered **natively by the cluster controller**: the host acknowledges them and removes all of its own screens. Identifiers above that range (audio, phone, messaging, turn-by-turn, voice, application list) are rendered **by the Android host on Display 1**. Navigation as ClarityLink means it is the second kind. (`HONDA_STATIC_CONFIRMED`)
3. **A displaying-status handshake gates the show.** When a host-rendered page is selected the host reports "waiting", builds the content, then reports "displaying"; it reports "none" for meter-native pages and "waiting" again when the display is removed. The controller therefore knows whether the Android layer is ready. This is consistent with the physical cluster showing content that depends on controller state and not merely on what exists on Display 1. How the controller uses the handshake is not in the preserved set. (`HONDA_STATIC_CONFIRMED` for the host half / `INFERRED` for the controller half)
4. **A selection change either resumes an existing screen or clears the host's own screens.** With no interrupt in effect, a changed selection resumes the screen that already exists for that content if there is one; otherwise the host removes all of its screens before building the new content (a meter-native selection builds nothing). Whether a third-party View added to a window root is removed by that is not shown. (`HONDA_STATIC_CONFIRMED` for the factory screens / `UNKNOWN` for injected Views)
5. **HondaHack rides this machinery.** Its page request is the same interrupt notification the host itself sends for ordinary interrupts; the host then receives the controller's resulting status record for the borrowed slot, builds that slot's factory content, and HondaHack's own View sits in the same root. (`HONDAHACK_STATIC`)

Consequences for the pane contract:

- `observe_contents` models the controller's decision correctly: a status record is the *only* trustworthy page signal, a warning content is one of its values, and anything unreadable must deselect. It also matches the safe reading of "interrupt status none" as no information.
- A real pane would need two authorizations, not one: the right to place Views in the host, **and** the right to have the controller select a host-rendered page for it. A View alone is not visible unless the controller is showing a host-rendered page and has been told "displaying".
- The page request is a CPU-communication message and shares a service with B-CAN traffic. Treat it as a vehicle-bus-adjacent operation, never as an Android-only call.

## 3. What the HondaHack logic means for a ClarityLink pane

These are design consequences, each tied to a behaviour in the preserved HondaHack code. They are not criticisms of that product and not claims about real-world faults.

| ID | HondaHack behaviour (`HONDAHACK_STATIC`) | Hazard if copied | ClarityLink rule (implemented in `navigation_pane_host.py`) |
|---|---|---|---|
| H1 | Visibility is derived from the last reported (id, status); "status none" means *unchanged*. | A missed or reordered callback leaves old visibility in place. | `observe_contents`: only an active navigation report selects the page; unknown and non-active reports deselect; older ticks are ignored; `expire_observation` deselects when the host goes silent. |
| H2 | Inserts into the **interrupt** root when that layout is visible, and brings itself to the front there. | Custom content could sit above factory warning Views if they share that root. | A pane never targets the interrupt layer. Its lease needs *no interrupt active*, and any interrupt revokes it. |
| H3 | Stop is a visibility flip; the view stays attached; frame arrival restarts it. | A frame arriving after "stop" can re-show content; a broken flip leaves content up. | Withdrawal is a **lease revocation** that clears queues and detaches. A frame never revives a pane: `resume()` is explicit and needs a fresh pane generation. |
| H4 | Takes the cluster by calling the host's own **LVDS-interrupt notification** for a different-purpose content slot. The host sends it (preceded by a neutral reset notification and a short delay) through the AP service to the CPU-communication service, which also carries B-CAN data. | The request is not an Android-UI-only act. Relative priority against real warnings is host- or controller-defined and was observed once (Door Open preempted casting). The slot's meaning to the cluster controller, and any vehicle-side effect, are unknown. | No such request exists in ClarityLink code and none may be added without a separate authorization that treats it as a vehicle-bus-adjacent operation (see CL-R10B bus-risk analysis). |
| H5 | Removal depends on HMI-service broadcasts; recreation on restart. | Content can outlive a host restart if the broadcast is missed. | Host loss, close and page loss all revoke the lease synchronously and drop every queued frame. Recovery needs a valid display and a fresh generation. |
| H6 | Geometry is HondaHack's own layout (a 584×215 root with a fill-parent ImageView). | Treating it as a physical aperture. | `Viewport.source` must be `SYNTHETIC_TEST` or `AUTHORITATIVE_MEASURED`. `LAYOUT_LOCAL_CANDIDATE` and `UNKNOWN` are refused, so the 584×191 figure can never enter the pane. |

## 4. Existing physical evidence, and what offline work can still answer

Before asking for any new car session, the preserved record was inventoried. The September 25 Maps/Music captures, September 28 factory-Navigation and HondaHack captures, Advanced Meter data, Display 1 screenshots, SurfaceFlinger and WindowManager dumps and the Door Open (Test 4C) recordings are in private storage. They establish full-frame 800×480 Display 1 output in every state, ownership of the full-frame windows by the host process, the presence of physical indicators absent from the capture, and one warning that preempted and then restored casting.

| Remaining gap | Can existing offline evidence answer it? | Result |
|---|---|---|
| Navigation-page exit and re-entry | The preserved captures are not synchronized to page changes. The HondaHack code now shows its visibility is a pure function of the reported content and status, so *its* behaviour on exit is statically determined (hidden on a different active content, unchanged on "none"). What the **host** does to the Views on exit is not. | Partly answered (HondaHack side). Host side needs observation. |
| "Stop Casting" restoration | Answered statically: it flips visibility and leaves the view attached (section 2, row 9). Whether the factory content beneath is intact is the unobserved part. | Partly answered. |
| Runtime View coordinates and clipping | Not derivable from static code or from the full-frame captures. | Needs observation. |
| Physical visible Navigation aperture | Not derivable from the Android frame. Needs a calibrated external recording or an authoritative coordinate source. | Needs observation. |
| Other warning classes | Warning is its own content identifier in the host's scheme, and also reaches the interrupt layer. Which classes use which route is not in the preserved data. | Needs observation or a deeper static trace of the content manager. |
| Host process loss or display replacement with injected content | Static: the factory side tears down and rebuilds; the injected side depends on HMI-service broadcasts. Dynamic outcome unknown. | Needs observation. |

The sharpest *offline* follow-up that remains is a bounded static trace of the host's content manager to learn which events change the selected content, which would sharpen row 1 and row 2 without touching the vehicle. It is listed in the [observation plan](../../docs/development/cl-honda-111-01-next-observation-plan.md) as work to do before any vehicle request.

## 5. Evaluating the existing API17 renderer for an authorized host

`src/claritylink-renderer/android-api17/` (PR #77, merged) already has the shape this contract needs, and the pane host's Python contract was aligned to it.

| Concern | API17 renderer today | Pane contract | Gap |
|---|---|---|---|
| Host supplied by the caller | `Display1OutputBackend.Host` with `getMainLayer`, `isNavigationPageActive`, `attachContent`, `detachContent`; root acquisition deliberately **not** implemented | `PaneHost.acquire/present/withdraw`; page and interrupt observed from the host | Needs an authorized host to implement `Host`. None exists. |
| Navigation-page gate | `attach` and `submit` throw when the page is inactive | Lease needs the page; deselect revokes | Java checks at call time; it does not subscribe to page change. A callback or lease object would close the gap. |
| Frames | CPU RGBA only, up to 3840×2160 and 4 MiB, row stride, rotation, crop, presentation time in ns; Surface frames are contract-only | `DecodedFrame` with the same fields and bounds; Surface refused | Parity achieved on fields and limits. |
| Generations | `generation` plus `replaceGeneration`; compositor and ledger are monotonic | Pane generation strictly increasing for the host's life; stream and config generations separate | Java has one generation; the pane model has three (stream, config, pane). A mapping is in the Codex handoff. |
| Warning | `FrameDispatchGate` fences draws against a warning epoch | Interrupt revokes the lease and clears queues | Java suppresses at draw time; the Python host revokes at event time. Both fail closed. |
| Viewport | `Viewport` fits 800×480; `RendererViewport` carries `SYNTHETIC_TEST_ONLY` provenance | `Viewport.source` must be admissible | Same philosophy; provenance enum is richer in Python. |
| Latency / resources | Backpressure gate; single owned frame | Bounded queue (1–8), latest-wins `pump`, every frame released once | Not measured on API17 hardware. No performance result is claimed. |
| Surface-backed zero-copy | Contract-only | Refused | Needs a separate API17 Tegra/MediaCodec investigation. |

**Bitmap versus Surface.** A Bitmap/Canvas path is what the preserved HondaHack route used and what the API17 renderer implements; a Surface-backed path would need a Surface owner that does not exist in this architecture. The existing API17 renderer cannot reach the Honda cluster without a valid factory admission boundary (Gate 2).

## 6. The pane contract, operation by operation

| Operation | Python (`navigation_pane_host.py`, `type111_pane_bridge.py`) | Fail-closed behaviour |
|---|---|---|
| Attach to a valid, authorized host | `PaneHost.acquire(owner)` → `PaneLease` | Denied unless display valid, page selected, no interrupt, admissible viewport, newer generation. `FactorySinkAdapter` always denies. |
| Confirm Navigation page | `select_navigation_page`, `observe_contents`, `expire_observation` | Unknown or silent means not selected. |
| Confirm a valid viewport | `set_viewport` | `LAYOUT_LOCAL_CANDIDATE`/`UNKNOWN` refused; change revokes. |
| Present new content | `present(lease, frame)` | Validates lease, frame, identity, order, storage, geometry. |
| Withdraw | `withdraw(lease)` | Always allowed. |
| Yield to interrupts | `activate_interrupt` | Cannot fail; revokes synchronously; clearing restores nothing. |
| Detach on page change / host loss | `select_navigation_page(False)`, `lose_display`, `close` | Synchronous revocation, callbacks contained and run once. |
| Restore factory content | `factory_content_visible` | True whenever the display exists and nothing of ours is shown. |
| Recover | `Type111PaneBridge.resume()` | Needs a live child, a valid host and a **fresh** pane generation; replays nothing. |
| Fail closed | all of the above | Malformed, stale, foreign, oversized and unsupported input are rejected and released. |

Test coverage for each row: `tests/honda/test_cl_honda_111_01_navigation_pane_host.py` and `tests/integration/test_cl_honda_111_01_type111_pane_bridge.py`.

## 7. Verdict for Gate 2

`DISPLAY_SUPPORTED_PATH_NOT_FOUND` is unchanged. The campaign added a reproducible account of *how the only demonstrated path decides what is visible* and what that implies for a safe contract, but not a permission, a coordinate system or a warning guarantee. See the [critical boundaries](../../docs/development/cl-honda-111-01-critical-boundaries.md).
