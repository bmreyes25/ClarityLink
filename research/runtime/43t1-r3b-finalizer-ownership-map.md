# 43T1-R3B — finalizer ownership map

**Scope:** static ownership map for the preserved `jmcs` path plus clearly separated hypothetical project ownership. This map does not claim a Type111 Setup seam or Honda integration.

```text
Honda-owned AirPlay session
  ├─ Honda per-session delegate record (fixed 11-word table)
  │    └─ Honda _AirPlayHandleSessionFinalized(session, context)
  ├─ Honda PlatformControl tearDownStreams
  │    ├─ recognized stock type 100/101/110 handling
  │    └─ unknown type 111 skipped in recovered parser
  ├─ Honda PlatformFinalize(session)
  └─ CF/CFLite object and response graph release paths

Honda-owned global interface record
  └─ one event_cb slot → (interface, event=SESSION_DESTROYED)
       └─ no session pointer, no append-only subscriber evidence

Project would own (hypothetical; not wired to Honda)
  ├─ Type111 child object and its project resource handle(s)
  ├─ listener resources
  ├─ opaque project session key + generation token
  └─ stale/duplicate-generation cleanup records

Shared / unclear
  ├─ raw Honda session pointer as an opaque lookup input only
  ├─ HTTP connection private context's conditional session pointer
  └─ project generation ↔ Honda session association (not established)

Unknown
  ├─ pointer reuse / stable Honda generation
  ├─ universal finalizer coverage and timing
  ├─ project resource behavior after crash/restart/power loss
  └─ Type111 CFLite field compatibility / interruption safety

Rejected unsafe replacement
  ├─ replacing Honda's per-session delegate table
  ├─ replacing global g_carplay_cbs event_cb record
  └─ overwriting dispatch/callback tables or redirecting code to reach project cleanup
```

| Resource / callback | Owner | Evidence label | Cleanup/reachability conclusion |
|---|---|---|---|
| Honda AirPlay session and context | Honda | `HONDA_CONFIRMED` | Session pointer/context reach Honda callback and PlatformFinalize in static finalizer path. |
| Honda Type110 stream entry and response containers | Honda | `HONDA_CONFIRMED` | Observed retain/release graph and recognized Type110 teardown path; scope is the hash-matched stock graph. |
| Honda session finalizer callback | Honda | `HONDA_CONFIRMED` | Fixed slot in Honda-owned delegate, called by `_Finalize`. |
| Global `event_cb` record | Honda interface consumer / shared registration surface | `HONDA_CONFIRMED` | Single whole-record replacement; callback gets interface and event but not session. Project replacement is rejected unsafe. |
| Project Type111 child | Project would own | `MODEL_ONLY` for historical contract; actual Honda insertion `UNKNOWN` | No Honda finalizer/cleanup set points to it. |
| Listener resources | Project would own | `MODEL_ONLY` | Host cleanup tests/policies only; not visible to Honda PlatformFinalize. |
| Project generation token | Project would own | `MODEL_ONLY` | No corresponding Honda generation value or callback argument. |
| Stale/duplicate cleanup record | Project would own | `MODEL_ONLY` | Exact-key handling exists only in offline registry contract; no Honda delivery path. |
| Connection private context session pointer | Honda connection / unclear relation to project child | `HONDA_CONFIRMED` | `_connectionFinalize` teardown is conditional on non-null pointer; no child registry lookup established. |

The ownership split is decisive: Honda cleanup owns Honda objects, while the proposed Type111 object/listener/generation would be project resources. No reviewed non-replacement edge transfers project ownership into Honda's cleanup graph. Do not use Type110's static release path as proof that Type111 will be enumerated or released.
