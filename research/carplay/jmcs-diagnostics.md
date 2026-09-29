# Existing `jmcs` device-manager diagnostics

Date: 2026-09-29. Offline-only review of the ignored, symbolized ARM ELF `extracted/system-vendor/system/bin/jmcs` (same hash as [Step 17](../../step-reports/17-carplay-registration-winner.md)), its embedded DWARF/symbols, extracted MCS XML, and tracked runtime evidence. No vehicle, ADB, network connection to the unit, process-memory read, signal, configuration change, or firmware change was used.

## Decision

**No safe pre-existing diagnostic was found that exposes the device-manager registration list or per-candidate results for `"CarPlay Screen"`.** The manager walk is `dev_attach` at VA `0x81ff4`; it calls interface slot `+0` and selects the strict greatest unsigned result, then calls slot `+4` through `dev_attach_to_app` (`0x81e64`). The walk contains no log call in the candidate loop. Its surrounding success/failure logs do not print candidate interface, score, name, or selected attach function.

### Potential devmgr diagnostic functions

| Function/symbol | Finding |
|---|---|
| `dev_attach` (`0x81ff4`) | The only located registry traversal relevant to matching. No candidate logging or output interface. |
| `devmgr_dev_attach` (`0x82858`), `devmgr_dev_attach_ex` (`0x82b80`) | Entry points into allocation/attach; not dump/list APIs. |
| `devmgr_app_register` (`0x8307c`), `devmgr_app_unregister` (`0x833ec`) | Mutating registration/removal paths, not diagnostic enumeration. |
| `devmgr_init` / `devmgr_uninit` (`0x821c8` / `0x823d4`) | Initialize/destroy manager; uninit's list activity is teardown, not a safe dump. |
| `devmgr_get_dev_ctx_d`, `devmgr_get_app_ctx`, resource add/remove | Handle/context/resource operations, not registry traversal output. |
| `selection_dump` (`0x3e9f4`), `mc_pb_evt_dbg_dump`, `mc_attr_dump`, `mc_attrset_dump`, `jdbg_hex_dump`, `m_dbg_dump`, `dump_thread_list` | Dump-like symbols exist, but no evidence connects them to `mc_devs` or the manager registration list. Do not invoke as devmgr diagnostics. |

Symbol/DWARF and string scans found no `devmgr_*dump/print/list/enum/status` sibling. The source-name strings include `mc_devmgr.c` and symbols retain names, but do not include recoverable C source.

## Registry traversal inventory

| Function | Purpose | Callers | Reads | Outputs | Side effects |
|---|---|---|---|---|---|
| `dev_attach` | Walk manager registration list; invoke each match callback; keep strictly greatest score; dispatch winner attach | `devmgr_dev_attach`, `devmgr_dev_attach_ex` through shared attach path | manager list at `+0x08`; node next `+0`, interface `+8`; interface callback slots `+0`, `+4`; secure device/request context | return status and attached device state; generic success/failure logs only | invokes arbitrary registered match callbacks; winner attach callback can mutate/device-attach; lock is held by caller. Not a diagnostic to invoke. |
| `devmgr_uninit` | Tear down manager | `mediacore_uninit` path | manager, devices, list, resources | logs lifecycle/failures | frees/unregisters/destroys state; unsafe and irrelevant for observation. |
| `devmgr_app_unregister` | Remove registration | registration owner cleanup | list node/interface | status | mutates registry. |
| `devmgr_dev_detach` | Detach device handle | device lifecycle callers | attached device/selected app | status | mutates active device state. |

No additional read-only traversal producing counts, names, serialized state, or status was identified. Generic media/storage routines may enumerate their own application-level records; they are not traversals of the registration list.

## Device-manager logging

| Log call/site | Format/data | Function | Level | Candidate details? |
|---|---|---|---|---|
| `os_log_print` (`0x13318`) call sites in `dev_attach` | Manager/attach lifecycle errors and generic status/timing; error paths include request/context and selected node values only in failure context | `dev_attach` | guarded by MediaCore debug-level checks | No per-candidate score, interface pointer/name, or `+4` callback. |
| `os_log_print` in `devmgr_init` / `devmgr_uninit` | initialization/teardown and error diagnostics | lifecycle functions | MediaCore module level | No entry enumeration; teardown messages are not a dump. |
| media-device attach/register log strings | Generic `media_dev_attach` and registration lifecycle, e.g. callback-registration failure / device metadata | media-device paths | MediaCore level | Not proven to correspond to the `"CarPlay Screen"` manager lookup; no score/winner table. |
| `__android_log_write` in `os_log_print` | Emits accumulated log buffer as Android log priority 2 | common logger | reached when internal buffer flushes | Sink only; it does not add registry fields. |

The exact string `"CarPlay Screen"` is passed into the attach path, but no existing trace prints each callback's score. `MATCH TRACE DIAGNOSTIC EXISTS: NO` on current static evidence.

## Log-level controls

| Setting | Default/evidence | Where read | What it enables |
|---|---|---|---|
| `/system/vendor/media/mcs/j_debug.xml` `DebugLevels/DMEDIA_SDK` | Extracted file sets `Level="E"` | `jos_debug_from_xml_init` / XML debug-level subsystem | MediaCore SDK error-level logging. The manager code consults internal module level before lifecycle log calls. Raising this would not make the absent candidate-loop log appear. |
| `DebugMonitor/Enable`, `Interval` | Commented out in the extracted `j_debug.xml` | debug monitor file-stat/XML path | Optional file-polled debug-level/config monitor. No devmgr dump behavior identified. |
| `uw_debug_set_level` / `debug_get_module_number` | Runtime level setter exists as a library symbol | internal debug subsystem | Changes module levels in process; no safe user-facing invocation found and no candidate trace exists to enable. |
| `mc_carplay_log_control` / `handle_carplay_set_log_ctrl` | Named control functions exist | MediaCore IPC control operation path | CarPlay logging controls; not shown to change devmgr candidate logging. Avoid treating as relevant. |

The source also imports `getenv`, but no evidence ties an environment variable to devmgr diagnostics. No `property_get`/`property_set` import was found. No setting should be changed; changing XML is a filesystem/config modification, and runtime setters are state changes.

## Startup arguments and init/service configuration

`main` is symbolized at `0x131c0`. Its body uses no `argc`/`argv`, option parser, help text, diagnostic mode, or console switch. It resolves its own executable path, calls `mediacore_init`, initializes `mc_server`, then waits for signals and tears down. Thus no supported `-h`, `--help`, `-d`, `-v`, `-dump`, `-status`, or `-console` argument was found.

The selected forensic extraction contains `/system/bin/jmcs`, MCS XML, and selected system files, but **does not contain init `.rc` service definitions**. Runtime process evidence identifies `/system/bin/jmcs` and root ownership; it does not preserve the service stanza, arguments, environment, or service options. Do not infer those missing fields. Available app configuration includes `j_config.xml` and `j_debug.xml`; no diagnostic argument or port-5000 configuration was found there.

## Binder, local IPC, and signals

- `mc_server_init` registers MediaCore operation dispatch (`init_server_op_map`) and dev-interface handling, then calls `j_ipcs_register_listener` with service ID `0x16` and its request handler. This is local IPC, not a documented devmgr list/dump command. Its parsed operation map has MediaCore controls; no registry enumeration or candidate-match operation was identified.
- Binder-related C++ symbols/imports (`BBinder::dump`, `BnJIpcService`, `BnJIpcChannel`) support the JMediaCore IPC service implementation. The imported base `BBinder::dump` symbol alone does not prove jmcs overrides or exposes a devmgr dump. No devmgr state contract or dumpsys command was found; classify devmgr dumpsys support **NO**.
- `main` blocks signals and waits with `sigwait`; the observed path distinguishes signal 17 for `waitpid` and otherwise enters orderly shutdown. No `SIGUSR1`/`SIGUSR2`/`SIGQUIT` state-dump handler was found. Do not send signals. A signal-triggered shutdown is not read-only.
- `debug_monitor_func` polls a debug XML/config file and schedules debug-level changes. It does not walk `mc_devs` or dump manager contents.

## Safety classification

| Candidate | Classification | Reason |
|---|---|---|
| Read current existing logs | READ-ONLY SAFE as an offline review; prior runtime logs are empty for manager match | No action required now; available past logs contain no match trace. |
| `dev_attach` / normal attach | STATE-CHANGING | Calls match functions and winner attach; mutates device manager and active device state. |
| `devmgr_uninit`, unregister/detach | STATE-CHANGING | Destroys or removes live state. |
| debug XML monitor / `uw_debug_set_level` | LIKELY READ-ONLY BUT UNPROVEN for log output; configuration/runtime state changes | No relevant per-candidate log exists. No change or invocation recommended. |
| MediaCore IPC server operations | UNKNOWN / potentially STATE-CHANGING | Existing service control operations are not proven safe for this task; no devmgr dump command found. |
| Binder `dump()` | LIKELY READ-ONLY BUT UNPROVEN in general; UNSUPPORTED for devmgr data | No jmcs devmgr dump implementation/contract identified. |
| generic `dump*` helpers | UNKNOWN | No demonstrated relationship to manager list; some traverse/dump unrelated or mutable state. |
| Signal shutdown path | STATE-CHANGING | Teardown and device callback unregistration follow. |

**Safe pre-existing diagnostic available: NO.** No future command/procedure is recommended from the current binary. No diagnostic was run.
