# R6C authentication API reuse

The narrowest **observed internal** operation is the `uwh_ipod_cp_*` family in `jmcs`: obtain/release, certificate length/read, set challenge, signature readiness/length/read, reset. `mc_carplay_uwh_ipod_cp_*` wraps it for CarPlay; `libcarplay_proxy.so` forwards a registered callback record. `os_auth_cp_*` owns the lower I²C access. These names and linked call sites are `HONDA_STATIC_CONFIRMED`; their exact arguments, output ownership, locking, error codes, and ABI stability are not reconstructed here.

| Candidate | Caller → callee | Lifetime / permissions | Clean-room reuse verdict |
|---|---|---|---|
| proxy callback facade | AirPlay/proxy → `jmcs` registered callbacks | Process-local singleton; registration during `mc_carplay_app_init`, unregister during shutdown | No external-session API. Another registration risks stock authentication. |
| `uwh_ipod_cp_*` | `jmcs` iAP/CarPlay code → internal functions | `jmcs` owns device and mutex; target device permissions unknown | Internal callable symbols are not a separately loadable library or supported IPC. |
| `os_auth_cp_*` | `jmcs` → I²C configured path | Opens factory device; ownership and contention unknown | Structural hardware path only; ClarityLink must not access it directly without an authorized, supported boundary. |
| CarPlay session handoff | factory owner → independent consumer | No handle, Binder method, socket protocol, or callback recovered | `EVIDENCE_REQUIRED`. |

The desired contract remains `authenticate(session) → opaque authenticated session`; it must carry a valid control transport and security context, not private material. The existing process-local signer facade is **insufficient** for R6B's `SessionHandoff`.
