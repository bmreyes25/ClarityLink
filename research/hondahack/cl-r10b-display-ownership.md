# CL-R10B — Honda cluster ownership and safe frame admission

**Status:** offline evidence audit; no Honda operation, installation, contact, or live test.
**Safety:** `safeForHonda() == false`. No ClarityLink Honda output backend is authorized by this report.

## Baseline and duplication control

The ClarityLink repository was clean on `feature/cl-hh-03-view-observability` at `dfddb787e3faecc7d897e74dd02537e4928c6d3a`; `origin/main` was `91562137448f78bc6a8b890d011b4c5185afea79`. A separate CL-R10A worktree was at `939e4566673bdab03f64d3ec0074c9f03a2732e2` with PR #47 open. Existing PRs #40, #43, #44, #45, and #46 cover prior receiver/output boundaries, readiness, geometry, and view observability. This report reuses those milestones and adds no duplicate geometry, display-enumeration, or decoder work. It was prepared on a new branch from `origin/main`; none of those worktrees or PRs was modified.

## 1. Executive findings

The Civic developer has since published a source repository. At the inspected `v0.0.2` release (commit `2b9844e4c174df281de99e8e084ae7ee52ad1f61`, 2026-07-09), the `Clusters` app creates a full-screen system overlay on the last enumerated display and calls private Honda display-control services. This is substantially more evidence than the original post, but it remains a Civic-specific vendor-service technique, not an OEM-supported interface description. The repository has no declared license, warns its APIs are unstable, and its install guide assumes USB ADB access; the Reddit author said the head unit was rooted with HondaHack.

The published source does **not** implement a robust ownership lease. Its normal service-destruction path removes the overlay, but does not show an inverse for the startup display-control call. The Reddit post says the handoff signal is reversed when the app is killed; the README only says a signal is sent at startup, and the install guide separately claims normal display restoration when stopping the app. These are different claims. The source closes its optional video path on the normal Lane Watch exit path, not in service destruction; no abnormal teardown recovery is demonstrated. Android process death does not guarantee callback execution. The full-screen overlay can obscure Honda content and warnings. Exact downstream cluster behavior and CAN effects of the vendor calls are unknown.

On the Clarity, preserved Honda evidence shows that Honda's external-display host owns Display 1's window roots and normal content. An exported Honda display-control Binder exists, but the examined interface has no arbitrary frame-source parameter. The host does not expose a usable cross-process frame endpoint; its rendering access is process-local. HondaHack demonstrates a private injection path into that host, not a supported third-party admission contract. No Clarity display-control operation has been shown to grant a Navigation viewport to a third-party renderer.

**Verdict: B. PRIVATE TECHNICAL PATH FOUND — SAFETY/AUTHORIZATION UNRESOLVED.** The Civic source and Clarity HondaHack evidence establish private technical precedents. They do not establish a credible supported ClarityLink frame-admission path. ClarityLink must not implement either as an adapter without an explicit, authorized integration contract and separate safety review.

## 2. Civic developer claims and verification

The public Reddit post was created 2026-04-27 UTC and edited the same day. The author reported that Android renders some Civic cluster Audio/Navigation content over HDMI; a custom app sends a signal so the head unit takes over display rendering, and the signal is reversed when the app is killed. The author also reported using exposed vehicle-data interfaces, including BCAN/FCAN-derived values, and installing through ADB on a rooted HondaHack head unit. Those are developer reports, not protocol documentation.

The author later published [alexpotv/Clusters](https://github.com/alexpotv/Clusters), released as `v0.0.2` on 2026-07-09. The checked release commit is [`2b9844e4c174df281de99e8e084ae7ee52ad1f61`](https://github.com/alexpotv/Clusters/tree/2b9844e4c174df281de99e8e084ae7ee52ad1f61). The repository describes Android 4.2.2 and 10th-generation Civic (2016–2021) support, but identifies itself as an unfinished hobby project; it has no declared license and says its APIs are unstable. Its `cluster-plugin-api` is an in-process Java screen interface; the host service manifest declares itself non-exported. It is not a stable external plugin-registration service for ClarityLink.

Relevant source anchors at that pinned commit:

- [`ClusterDisplayService.java`](https://github.com/alexpotv/Clusters/blob/2b9844e4c174df281de99e8e084ae7ee52ad1f61/app/src/main/java/com/example/clusterapp/ClusterDisplayService.java) selects `DisplayManager.getDisplays()[last]`, obtains a display context, and creates a full-screen `TYPE_SYSTEM_OVERLAY` window. The source comments mark an app-selected subregion, but this is not an OEM aperture specification.
- The same service binds to Honda display-control services and requests display/content changes. It separately requests opening and closing an optional video path. The source provides no compatibility, permission, or authorization guarantee for these private operations.
- [`AndroidManifest.xml`](https://github.com/alexpotv/Clusters/blob/2b9844e4c174df281de99e8e084ae7ee52ad1f61/app/src/main/AndroidManifest.xml) requests `SYSTEM_ALERT_WINDOW`; the install guide states API 17 grants manifest permissions at install. The app's own service is non-exported. This does not prove a stock, unrooted Honda installation or bind/access policy.
- [`INSTALL.md`](https://github.com/alexpotv/Clusters/blob/2b9844e4c174df281de99e8e084ae7ee52ad1f61/INSTALL.md) says stopping the app removes the overlay and restores the normal display. The source's `onDestroy()` removes the overlay and unbinds; it does not issue an evident inverse for the startup display-control request. Normal callback cleanup is not crash/power-loss proof.

The author's public GitHub repositories were checked. `Clusters` contains the relevant code; the separate `9CarPlay` repository does not appear to be the cluster app source. The report does not infer that every branch, device variant, or later unpublished update has been audited. The owner has not been contacted. No tests were run against the Civic code or a vehicle.

## 3. Honda display-host architecture

The preserved Clarity evidence supports this ownership chain. Existing offline source review and read-only captures establish the host relationship summarized below; private package, symbol, and capture identifiers are omitted.

```text
Android DisplayManager / Display 1
    -> Honda-owned external-display process
       -> vendor-managed full-window root hierarchy
          -> Honda Navigation/TBT/audio/menu/interrupt content
    -> downstream cluster composition (transform and mask unknown)
```

The Honda display host selects an external display and creates its window hierarchy. Saved read-only captures show full-frame 800×480 Display 1 output. The physical cluster includes fixed gauges/status content absent from the Display 1 capture, so Display 1 is not the complete physical cluster image. No exact factory Navigation aperture or downstream transform is established.

Navigation-page selection and content callbacks are mediated by Honda-owned display/AP/navigation components. The evidence identifies semantic Navigation/TBT state and the host's main/interrupt root management; it does not identify a third-party operation that acquires ownership of the Navigation region. The host owns its windows and views; no separate owner token, frame source callback, public registration, or documented revoke/restore API was found.

The known HondaHack route uses Xposed code in the external-display process to insert custom Android content into Honda-owned display windows. Its input arrives through a separate bitmap path. This is direct evidence that code executing in that host process can compose content. It does not give an ordinary ClarityLink process the same authority. Class names, hook sites, and attachment details remain in the existing private research record.

## 4. Ownership mechanism candidates

| Hypothesis | Evidence and owner | Permissions / bus / warning / restoration | Admissibility and minimum proof |
|---|---|---|---|
| A. Honda system-service transfers Navigation ownership | Clarity has an exported display-control Binder surface; no ownership lease or viewport grant was found. Civic source calls private display controls, but it does not document a supported ownership protocol. | Effective Clarity caller permissions and method checks are unknown. Vendor display calls may affect display routing; CAN effects are unknown. Warning priority and crash restoration are unproven. | **Not admissible.** Need an OEM-supported Clarity method contract specifying authorization, scope, warning precedence, revocation, and failure restoration. |
| B. Honda app/service registers approved third-party content | No Clarity plugin or frame registration API found. Civic's `ClusterPlugin` is an in-process class used by a non-exported host, and its APIs are called unstable. | Requires private host access on Civic; Clarity signing/binding rules unknown. No safety or bus guarantee. | **Not admissible.** Need an exported, documented API/sample and supported signing/permission path for this exact Clarity firmware. |
| C. Binder returns a privileged Navigation presentation surface | The inspected Clarity display-control Binder carries control/status data, not arbitrary pixel or stream output. No surface handoff was found. | No surface authorization, revocation, warning policy, or crash recovery contract. Any vehicle side effects unknown. | **Not admissible.** Need a receiver-side contract plus runtime permission and lifecycle evidence, without invoking undocumented operations. |
| D. Civic private IPC / display state | Confirmed in Civic source: overlay on the external display plus private Honda display-control Binder calls. Their exact semantic effects are not established by the third-party source. Civic author separately reports BCAN/FCAN data access. | `SYSTEM_ALERT_WINDOW` and root/ADB installation are reported/declared; source does not prove no privileged signing requirement on another build. Vendor calls may affect vehicle/display control; CAN reachability is unknown. Full-window overlay can cover host content. Callback cleanup is insufficient for process/power loss. | **Research only; not portable.** Need developer clarification and matching Clarity-owned evidence, authorization, warning behavior, and crash recovery. No commands to be replayed. |
| E. Android API 17 `Presentation` / secondary display | Android added `Presentation` and `DisplayManager` at API 17. This is a window on a display suitable for presentations, not a lease on a Honda-owned Navigation region. Honda's saved evidence shows host-owned full-frame roots and no evidence that a regular app's Presentation is admitted on its Display 1. | Android display removal dismisses a Presentation, but Android does not promise Honda warning priority, Navigation-page coordination, or return to factory content for this use. A system overlay is a different and potentially occluding route. | **Generic API capability only; not admissible.** Need supported permission/display admission and measured host z-order plus authoritative region/warning/restore contract on this build. |
| F. Clarity HondaHack Xposed insertion | Static third-party analysis identifies a private Xposed route into the Honda external-display process. | Requires code execution in a Honda process through a rooted/injected environment. It can add content to Honda-owned windows; ordering and priority are implementation-controlled. Prior footage documents one Door Open preemption/restoration only. Crash/host restart behavior is incomplete. No evidence that the traced pixel route itself sends CAN. | **Technically demonstrated; research-only and unauthorized for ClarityLink.** Need independent compatibility, authorization, security and full lifecycle review; it is not an OEM extension contract. |

None of these observations equates technical reachability with permission. No HondaHack hook, private Binder transaction, CAN operation, vendor binary modification, or vehicle test is proposed.

## 5. Binder/service evidence and frame admission

The Clarity display-service manifest, Binder interface, and host-service evidence were reviewed offline. In the inspected surface:

- The display host has no usable cross-process frame endpoint; window/content access is process-local.
- The exported Honda display Binder is a control/status surface. Its examined operations carry control metadata, not arbitrary pixels, a decoded frame source, or a CarPlay stream descriptor.
- Manifest export is not proof that an arbitrary caller passes framework/signature checks or may override content.
- HondaHack's Xposed injection is the only preserved Clarity frame-to-root example. It obtains access by executing inside the host process.

Thus the smallest missing interface is an **authorized Honda-owned frame-admission/revocation contract** that binds caller identity to the active Navigation display and exposes an accepted frame source or host-owned presentation callback. A service name, display ID, private control call, host window, or successful overlay alone does not provide that contract.

## 6. Vehicle-bus risk analysis

| Operation / path | Evidence classification | Bus-risk class | Finding |
|---|---|---|---|
| Civic app window creation on Display 1 | Public source implementation | Android UI presentation | `TYPE_SYSTEM_OVERLAY` on a vendor secondary-display context. It can visually cover Honda output; not a Honda-supported region grant. |
| Civic private display-control Binder calls | Public source implementation; service semantics not independently verified from Civic evidence | Unknown; potentially vehicle/display control | The app calls Honda vendor display services. The available public source does not establish whether these effects are Android-only or reach a vehicle bus. Do not replay. |
| Civic optional video-path control calls | Public source implementation; service implementation/route effects unknown | Unknown; potentially vehicle/display control | A Lane Watch path requests opening/closing a vendor video route. Do not infer CAN absence or Clarity compatibility. |
| Civic BCAN/FCAN data source | Public source implementation and developer report | No direct CAN transmit call found in inspected app paths; active vendor-service requests occur and their side effects are unknown | Source registers listeners, enables receive subscriptions, initializes a diagnostic service, and periodically submits bus-data requests. This is not a complete audit of vendor middleware or all app code. |
| Clarity Navigation/TBT guidance setters | Preserved Clarity static findings | **Potential vehicle-bus output** | Existing research identifies possible downstream B-CAN effects. These are semantic guidance operations, not frame admission. Do not invoke. Exact symbols are omitted from this public report. |
| Clarity display-service callbacks/status operations | Preserved Clarity static interface | Unknown unless individually audited | Control/status names do not prove output-only or bus-free semantics. No speculative method calls. |
| Existing Clarity HondaHack drawing hook | Preserved static HondaHack analysis | Android view composition for the traced pixel path; broader module can use other interfaces | No direct CAN write was identified in the traced screen-cast pixel path. This conclusion does not generalize to all HondaHack features. |

No vehicle-bus command was issued. For a future path, require call-graph/source proof that the chosen admission and release operations do not send CAN or alter cluster control messages, or obtain a separately authorized control specification and safety review.

## 7. Navigation-page ownership, warnings, and failure recovery

The matrix records only expected fail-safe behavior and what evidence exists. It does not claim the Honda implementation already meets each requirement.

| State / transition | Legitimate owner and safe expected visible result | Required authority/frame behavior | Current evidence |
|---|---|---|---|
| A. Factory Navigation idle | Honda host | Honda draws its normal idle content. | Honda-owned views shown by static host evidence; exact physical aperture unknown. |
| B. Navigation selected | Honda host unless a supported grant exists | Any external renderer must acquire a bounded, revocable grant tied to this state. | No grant API found. |
| C. Navigation deselected | Honda host | Withdraw/clear external frame immediately; never retain stale map pixels. | Xposed callback behavior is partial; no complete ClarityLink contract. |
| D. ClarityLink attached | Honda remains authority until authorization succeeds | Validate caller, session, display, and generation before accepting frames. | No supported attach contract. |
| E. ClarityLink drawing | Honda owns composition; delegated surface only under explicit grant | Accept only authorized frames for current generation; isolate from primary Honda content. | HondaHack proves private injected view only. |
| F. Factory warning active | Honda warning/interrupt owner | Honda warning must preempt external content; revoke or suspend frame submission. | One Door Open Test 4C clip reportedly preempts and restores. Universal warnings and z-order are unknown. |
| G. Warning dismissed | Honda host first, then a still-valid authorized grant | Re-check active Navigation and generation; never replay stale frame. | One recorded restoration only; no standardized callback contract. |
| H. Renderer failure | Honda host | Clear frame and release grant; Honda resumes without waiting for app. | Required behavior only; not demonstrated for HondaClarityLink. |
| I. Honda host process failure | Android/Honda service manager and Honda host on restart | All child ownership expires; host recreates factory roots and rejects stale producer. | Root lifecycle removal is static; recovery with injected renderer not proved. |
| J. External display removed | Android display/window manager, then Honda host | Cancel output; invalidate display identity/generation; wait for new host authorization. | API17 DisplayManager has removal events; Honda route recovery unknown. |
| K. ClarityLink stopped | Honda host | Revoke frames and release any grant; avoid a stuck display mode. | Civic app `onDestroy` removes overlay; abrupt process death/power loss not established. |
| L. Factory Navigation restored | Honda host | Stock Navigation is visible and current; no stale ClarityLink layer remains. | Civic install guide asserts restoration on stop; Clarity source evidence has no approved restore operation. |

Preserved Test 4C footage covers one Door Open interrupt and return. It does not establish universal warning priority, all warning classes, safe z-order, a Honda callback to ClarityLink, process-crash recovery, or Navigation exit/re-entry behavior.

## 8. Architecture comparison

| Architecture | Feasibility | Privilege and ownership | Warning / failure / restoration | Decision |
|---|---|---|---|---|
| 1. Supported Honda-owned renderer delegation | Best architectural fit, but no Clarity API found | Would keep Honda host as composition owner and pass only an authorized secondary frame/surface. Requires OEM-granted scope and lifecycle. | Can preserve warnings if host enforces priority; crash recovery can be host-owned. Neither is currently specified. | Preferred future target only if Honda documentation or an authorized sample appears. No implementation now. |
| 2. Independent Android presentation | Generic API17 capability exists | App creates a window on an eligible display; does not become owner of the Navigation region. Display eligibility and effective privileges on this unit unknown. | Android dismissal on display removal does not guarantee Honda warning priority or factory Navigation restoration. Full-screen overlay may occlude warnings. | Not a safe candidate under current evidence. |
| 3. Private Xposed View insertion | Technically demonstrated by HondaHack | Requires private code execution inside Honda's external-display process and accesses process-local display structures. | Can alter Honda content ordering; exact warning ordering and host/crash restoration only partially evidenced. | Research-only. Do not make it ClarityLink's production integration. |
| Civic private display transaction plus overlay | Demonstrated in public Civic source at pinned commit | Depends on Civic private vendor services and Android overlay permission; may be tied to that head unit/firmware. | Source removes the overlay on normal teardown; signal reversal and abnormal recovery are not established by implementation. | Useful comparator, not a portable Clarity API. |

## 9. Preferred candidate and contract requirements

No evidence-backed Clarity output-admission candidate is ready for implementation. If a Honda-authorized host contract is later obtained, the narrow adapter should sit **inside or behind the Honda-owned external-display host**, at the point where that host composes the Navigation root. It should accept decoded secondary frames through a host-issued, revocable capability and leave primary/Type110 and all Honda controls owned by the stock services.

The future contract must specify:

1. Session and display identity issued by the Honda host; caller/package identity and the exact authorization check.
2. A per-grant generation/nonce; frame metadata and source; bounded queue/backpressure and frame validation.
3. An explicit active-Navigation condition; no acquisition while another page owns the region.
4. Warning preemption that is host-controlled and immediate, with revocation/suspension semantics and no untrusted reassertion.
5. Idempotent release, timeout/lease expiry, process death, host restart, display removal, and partial initialization behavior.
6. Host-owned cleanup and factory Navigation restoration, proven independently of app `onDestroy()`.
7. A declared bus-effect boundary: Android presentation only, or exact vehicle-side effects with an authorized specification.
8. Isolation: no replacement of stock receiver/session, no Type110 displacement, and no changes to safety-critical vehicle functions.

**Not currently evidenced:** all Honda-issued capability/session/generation fields, frame callback, exact viewport, warning policy, bus-free guarantee, and revoke/restore semantics. **Must not be fabricated:** permission tokens, ownership signals, Honda callbacks, Binder transaction numbers, or an assumption that a `Presentation` owns the Navigation region.

## 10. Rejected approaches

- Treating an exported Honda display-control service as arbitrary rendering permission.
- Replaying Civic private display-control operations against Clarity or treating them as frame grants.
- Replacing Honda's external-display service or the authenticated CarPlay receiver.
- Using Xposed/root hooks as a production ClarityLink API.
- Treating API17 `Presentation` or `TYPE_SYSTEM_OVERLAY` as proof of safe cluster ownership.
- Treating the Civic README's normal termination claim as crash/power-loss restoration proof.
- Calling Navigation/TBT setters as harmless display controls; preserved Clarity evidence classifies some as potential B-CAN output.
- Repeating display enumeration, generic SurfaceFlinger inspection, frame decoding, or geometric estimates already completed in prior milestones.

## 11. Evidence ledger

| ID | Assertion | Source/version | Class | Confidence / remaining uncertainty |
|---|---|---|---|---|
| C1 | Civic author reported HDMI cluster rendering, a takeover signal, signal reversal at kill, BCAN/FCAN data, and rooted ADB installation. | [Reddit post, 2026-04-27 UTC](https://www.reddit.com/r/CarHacking/comments/1sxco3r/10th_gen_honda_civic_gauge_cluster_hack/) | Third-party developer report | High confidence the statements were posted; mechanism and abnormal restoration unknown. |
| C2 | Civic app creates full-screen overlay using last display; makes private display Binder calls. | `Clusters` v0.0.2, commit `2b9844e…`; [`ClusterDisplayService.java`](https://github.com/alexpotv/Clusters/blob/2b9844e4c174df281de99e8e084ae7ee52ad1f61/app/src/main/java/com/example/clusterapp/ClusterDisplayService.java) | Public third-party source implementation | High for source behavior; runtime behavior and exact OEM semantics unknown. |
| C3 | Civic screen plugin interface is internal to a non-exported service; API unstable/no license. | Same release; [README](https://github.com/alexpotv/Clusters/blob/2b9844e4c174df281de99e8e084ae7ee52ad1f61/README.md), [manifest](https://github.com/alexpotv/Clusters/blob/2b9844e4c174df281de99e8e084ae7ee52ad1f61/app/src/main/AndroidManifest.xml) | Public third-party source | High; exact legal status should be checked before any reuse. No source copied. |
| H1 | Honda external-display host owns Display 1 windows and normal content. | Bounded static host review and prior read-only display captures; PRs #43/#44 add related boundary documentation | Direct static evidence + recorded read-only runtime evidence | High for Android host ownership; downstream physical composition unknown. |
| H2 | Clarity display-control Binder has no arbitrary frame endpoint. | Bounded static Binder interface review | Direct static evidence | High within examined interface; no whole-firmware theorem. |
| H3 | HondaHack inserts custom content from within the Honda external-display process. | Existing private static analysis and captured output; internal report paths intentionally omitted | Direct static evidence + recorded Honda runtime evidence | High for the traced route; not OEM-authorized and not a standalone app API. Detailed implementation remains private. |
| H4 | One Door Open event preempted content and restored it. | Prior Test 4C report; original footage not present in the audited tree | Recorded Honda runtime evidence (prior report) | Limited to one warning/state; mechanism and generality unknown. |
| H5 | API17 `Presentation` exists, but does not grant Navigation ownership. | [Android `Presentation` API](https://developer.android.com/reference/android/app/Presentation), [DisplayManager API](https://developer.android.com/reference/android/hardware/display/DisplayManager) | Documented Android behavior + inference for Honda | High for API availability; Honda display eligibility and z-order unknown. |
| H6 | Some Clarity Navigation guidance operations may reach B-CAN. | Bounded static Navigation/control-path review | Direct static evidence | Medium/high for the examined paths; no operation invoked. |
| H7 | No Honda-owned approved frame admission/revocation contract was found in examined evidence. | Bounded manifests, Binder interfaces, host code and HondaHack path reviewed for CL-R9/CL-R10B | Negative finding from bounded search | Medium/high within examined materials; cannot prove no undocumented service exists elsewhere. |

## 12. Outstanding external questions

**Draft only — not sent.**

> Hi, I’m researching a 2018 Honda Clarity head unit with a related Android external-display architecture. Thanks for publishing `Clusters`; the source helps clarify the display path. I’m trying to understand the boundary and recovery behavior, not request credentials or proprietary source. If you’re comfortable sharing:
>
> 1. Which service/interface or IPC operation is the rendering handoff, and what does it authorize?
> 2. Does it require root, a system signature, or privileged permissions on the tested unit?
> 3. Is the operation Android display control only, or can it cause B-CAN/F-CAN or other vehicle-control messages?
> 4. Is handoff/restore managed by a Honda service, or by your app's overlay lifecycle?
> 5. What happens after process crash, force-stop, or head-unit power loss?
> 6. What happens during a factory warning or Navigation page change?
> 7. Which Civic head-unit firmware and Android build did you test?
> 8. Could you share a minimal API description or safe pseudocode, without confidential details?
> 9. Is the published `Clusters` repository the complete relevant implementation, and are there planned releases?
>
> Thanks; no need to share private source or anything that could affect vehicle safety.

These questions are external dependencies only; the report is complete without a reply. No message was sent.

## 13. Offline tests and validation

No new code or lifecycle model was justified. CL-HH-02 already models geometry; CL-HH-03 already models view observations; earlier API17 and lifecycle milestones cover synthetic renderer behavior. Additional synthetic tests cannot prove Honda's private Binder semantics, warning priority, or crash restoration. No tests were run for this report-only change.

Publication checks still required: Markdown/link/whitespace review, public-safety review, separate ECC code and security review. No Honda, ADB, iPhone, CAN, installation, framebuffer, Xposed, or firmware operation was performed.

## 14. Next engineering milestone

**CL-R10C: obtain and review an authorized Clarity host contract.** First request the Civic developer's clarification using the draft above (not sent here), while independently seeking a Honda-authorized API/sample or a documented Clarity host integration specification. Continue only if evidence identifies caller authorization, a bounded Navigation frame source, warning preemption, teardown, crash recovery, and a demonstrably safe bus boundary. If none appears, keep the Honda integration blocked and pursue an OEM-supported display route; do not implement Civic Binder calls or Xposed hooks.

### Final answers

1. **Does the Clarity have evidence of the Civic-style ownership handoff?** No equivalent supported handoff is evidenced. Clarity has HondaHack's private in-process rendering path; Civic source shows private Binder/display controls.
2. **What component would own a handoff?** For Clarity, only Honda's external-display process currently owns the Android display roots. No delegated ownership component/API was found.
3. **Android-only or potentially CAN-affecting?** Civic source uses Android overlay plus Honda vendor control Binders; bus effect is unknown and potentially vehicle/display control. Do not classify it as Android-only. Clarity TBT setters have potential B-CAN effects.
4. **Can it preserve factory warnings?** Not proven. One Door Open preemption observation does not establish general warning priority.
5. **Automatic factory restoration after failure?** Not proven for crash/power loss. Civic source shows normal teardown; Clarity recovery contract is absent.
6. **Can decoded Type111 frames theoretically use it?** A decoded bitmap could technically be drawn by a View, but there is no authorized Clarity frame-admission interface. Type111 does not confer display authority.
7. **What remains unknown?** Exact Civic Binder semantics, bus effects, grants/signature, Clarity equivalent, physical viewport, warning z-order, Navigation transitions, process-death recovery, and OEM authorization.
8. **Decisive evidence?** A Honda-authorized Clarity API/sample with caller authorization, host-owned frame callback, viewport, bus-effect declaration, warning/revocation behavior, crash recovery, and factory restore semantics.
9. **Is a physical test justified now?** No. First close the offline authorization/interface gap. This campaign authorizes no future vehicle test.

**Final verdict: B. PRIVATE TECHNICAL PATH FOUND — SAFETY/AUTHORIZATION UNRESOLVED.**
