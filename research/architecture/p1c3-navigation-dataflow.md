# P1-C3 — navigation producer-to-consumer dataflow

The chains below use the hash-matched `jmcs` and preserved decompiled Android packages described in [the audit](p1c3-iap2-route-guidance-ingress.md). Arrows marked `?` are missing evidence, not inferred calls.

```text
iPhone Apple Maps/Waze active route
  ? negotiated iAP2 Route Guidance message / app identity / fields
  ? jmcs decoded Route Guidance handler
  ? external subscription or authenticated IPC
  ? no-APK ClarityLink consumer                 NOT PROVEN

iPhone CarPlay control/ownership state
  -> stock CarPlayService OwnershipControl / PhoneControl
  -> onAbortCarPlayNavigation(boolean) / onCarPlayCallEnable(boolean)
  -> CarPlayApService RemoteCallbackList
  -> stock NavigationApService CancelRoute     STATUS_ONLY
  ? no-APK external admission                 UNKNOWN

expected Honda navigation responder (actual sender unverified)
  -> RES_ROUTE_INFO broadcast
  -> NavigationApService RouteInfo receiver
  -> ISetRouteInfoListener.onGetRouteInfo(String)
  -> CarPlayApService NavigationControl native-route-status flag
                                                HONDA_NATIVE_NAVIGATION_ONLY

Android Auto navigation
  -> NavigationApService Android Auto callback path
  -> TBTInformation / meter-related service    ANDROID_AUTO_ONLY

jmcs JMediaCore generic channel
  -> Parcel + channel context callback
  ? payload producer/schema/session association
  ? no-APK consumer                            UNKNOWN
```

## Exact traced edges

| Edge | Source evidence | Limit |
|---|---|---|
| Native iAP2 control/session | `jmcs`: `iap2_session_handler 0x200090`, `iap2_core_rcvd_control 0x2092bc`, `iap2_core_rcvd_ea 0x20b79c`; [Identification](../iap2-identification.md). | Generic dispatch, no identified route message ID or maneuver decoder. |
| CarPlay boolean production | Sibling decompilation `CarPlayService/.../OwnershipControl.java:520–530`, `PhoneControl.java:719–732`; callback schema `ICarPlayApServiceCallbackForNavi.java`. | Cancellation/call status only. |
| CarPlay boolean subscription | `CarPlayApService.java:1468–1490`, `NavigationApService.java:1289–1298`, `CancelRoute.java:75–89`; `RemoteCallbackList`. | Additional callback admission from a temporary native process unproved; no maneuver fields. |
| Honda route request | `CarPlayApService.java:653–665` → `Navigation/RouteInfo.java:43–61,101–116`, `GET_ROUTE_INFO` broadcast. | Request alters factory-navigation service work queue; not passive. |
| Honda route response | `Navigation/RouteInfo.java:29–40,119–154` receives `RES_ROUTE_INFO`, then `CarPlayApService.java:2067–2073` → `NavigationControl.java:81–101`. | Honda navigation broadcast contract; actual sender unverified. Consumer reduces it to a boolean native route flag. |
| Honda TBT and Android Auto | `NavigationApService.java:94,1331–1345,3112–3174` and `HondaNavigationLib` meter classes. | Separate native/AA provenance; some setters can affect vehicle output. |
| JMediaCore native Binder | `jmcs` `handle_data_received 0x264c90`; channel context callback via `blx r3` at `0x264cf2`; generic `createChannel`, `sendData`, `setListener`, `destroyChannel` symbols. | No route field/ID, session source, consumer permission or external subscriber demonstrated. |

`Navigation` manifest declares a service with Honda navi and TBT actions, while `CarPlayService` manifest exports its service without a component-level bind permission. Manifest declarations do not establish effective caller admission. ExternalDisplay/cluster services expose display control and native/AA status paths, not a verified authenticated iPhone maneuver feed. No source-to-consumer chain above provides a permissible, passive authentic route stream to ClarityLink.
