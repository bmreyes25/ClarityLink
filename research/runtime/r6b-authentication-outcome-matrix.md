# R6B authentication outcome matrix

| Outcome | Missing or achieved boundary | Public/legal closure source | Hardware | Code |
|---|---|---|---|---|
| HOST_AUTH_SESSION_READY | real authenticated ClarityLink control session | user-owned supported MFi system plus host handoff | usually yes | handoff adapter |
| HOST_AUTH_ADAPTER_PARTIAL | interface and replay work, no real authority connected | licensed service or genuine user-owned accessory API | possibly | concrete adapter |
| HOST_AUTH_HARDWARE_REQUIRED | no authorized authentication device/service | approved MFi coprocessor/accessory or licensed service | yes unless service supplied | hardware bridge + host session owner |
| HOST_AUTH_RESTRICTED_DEPENDENCY | only recovered/shared keys or restricted material offered | stop; choose authorized hardware/service | yes or authorized service | no workaround |
| HOST_AUTH_NO_LAWFUL_PATH_FOUND | no usable authorized route identified | stop and reassess | unknown | unknown |

Current engineering result: adapter boundary and synthetic replay work; no live authority is connected. The documented PlayPort default shared-key route is **RESTRICTED** under R6B. A genuine coprocessor or licensed service, plus an authenticated control-session handoff, is required to progress. No user-owned hardware/service has yet been established in this checkout.
