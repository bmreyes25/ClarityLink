# P1-C3 — conditional authentic metadata adapter contract

No production adapter is implemented because no authentic iPhone metadata source plus admitted no-APK subscriber was proven. This contract is a gate for later evidence, not a proposed stock interface or authorization for Honda operation.

| Gate | Required evidence | Current state |
|---|---|---|
| Source | Apple Maps or Waze active-route identity, app/version, and documented or observed semantic payload provenance. | Neither verified on this Honda. |
| Ingress | Negotiated iAP2 Route Guidance feature, exact message family, decoded fields, authenticated session/channel association and ordering. | Generic iAP2 control stack only. |
| External delivery | Actual stock producer → Binder/socket/other endpoint; permission and no-APK caller admission; additional-client semantics. | No authenticated route subscriber. |
| Lifetime | Generation or nonreused session identity, route start/update/reroute/cancel, device detach, stale-data expiry and cleanup. | No external contract. |
| Isolation | Read-only subscription and independent rendering; no Type110, MFi auth, factory nav, meter or Android Auto mutation. | Cannot prove until an endpoint exists. |
| Privacy | Minimal in-memory route data, no trip/coordinates in public logs or Git; explicit retention and disposal. | Design requirement. |
| API17 | Android 4.2.2 Binder/socket compatibility, UID/signature permissions, scheduling, process restart and service death. | Unverified for a new caller. |

If every gate is established, a smallest adapter would normalize **only evidenced fields** into the existing session-generation/lifecycle and navigation presentation models, then expire them on source loss. Possible fields such as road name, lane, distance, ETA, and route generation are **hypothetical design placeholders**, not a decoded Honda schema. Synthetic fixtures may test presentation but must never be labeled live Apple Maps/Waze data. An independent MapKit or third-party route is a different source and cannot claim to mirror the active phone navigation session.
