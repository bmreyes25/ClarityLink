# Step 20 — offline `jmcs` diagnostic discovery

Date: 2026-09-29

## Scope and method

Offline-only review of the local ignored `/system/bin/jmcs` ELF (ELF32 ARM with `.symtab` and DWARF), `nm` symbols, ARM disassembly at `main`, manager, server/IPC, signal, logging and socket routines, extracted `j_config.xml` / `j_debug.xml`, selected forensic extraction contents, and prior tracked `/proc` socket evidence. No ADB, vehicle, iPhone, debugger, ptrace, signal, port connection, configuration edit, firmware edit, or process-memory access was used.

## Results

### Device-manager diagnostic

**No safe pre-existing diagnostic exists in the inspected binary/configuration.** Symbols/DWARF and strings revealed no devmgr dump/list/enumerate/status sibling. `dev_attach` (`0x81ff4`) traverses list nodes, invokes interface slot `+0`, keeps the strictly highest score, and sends the winner to `dev_attach_to_app` (`0x81e64`) for slot `+4`. The candidate loop has no logging. Surrounding lifecycle/error logs do not expose the candidate names, scores, interface pointers, or winning callback. Other dump-like symbols are for unrelated structures, buffers, selections, threads, or attributes.

The `DMEDIA_SDK` debug default in `/system/vendor/media/mcs/j_debug.xml` is `E`. A config-polling debug monitor and internal `uw_debug_set_level` exist, but no candidate-loop log exists to unhide. Raising levels would change runtime/config state and still would not provide the requested trace. No setting was changed.

### Startup and service configuration

`main` (`0x131c0`) takes no parsed command-line options: no argc/argv option parsing or help/diagnostic/console mode. It initializes MediaCore and its IPC server, then waits for signals. The selected forensic extraction has no init `.rc` service stanza for jmcs; command-line arguments, user/group, environment and service options cannot be reconstructed from this offline copy. `j_config.xml` and `j_debug.xml` are present and contain no diagnostic argument/endpoint setting.

### Port 5000

Step 19 proved two `jmcs`-owned runtime LISTEN sockets on `0.0.0.0:5000` and `[::]:5000`, FDs 17/18. Static code does not attribute these sockets to a structured command server. `ServerSocketOpen` (`0x2a0a34`) is used by AirPlay receiver setup; traced ScreenSession setup supplies port 0 and publishes the assigned port. The runtime port-5000 role remains **UNKNOWN**. No parser/command table or read-only command can be assigned. No connection was attempted.

### IPC / Binder / signals

`mc_server_init` registers MediaCore operation dispatch and `j_ipcs_register_listener` service ID `0x16`; no devmgr registry list/dump operation was found, and the endpoint is not tied to TCP port 5000. Binder support symbols exist for JMediaCore IPC, including an imported base `BBinder::dump`, but no jmcs devmgr dump implementation/contract or dumpsys support was identified. `main` uses `sigprocmask` + `sigwait`; no `SIGUSR1`/`SIGUSR2`/`SIGQUIT` state-dump handler exists in the traced path. A signal path enters shutdown/teardown, not a read-only dump.

### Match trace

`MATCH TRACE DIAGNOSTIC EXISTS: NO` on inspected static evidence. There is no existing mechanism to obtain the candidate score table, slot `+4`, or winning interface without a runtime state observation. No diagnostic was run.

## Decision gate

| Question | Result |
|---|---|
| DevMgr dump function | None found |
| DevMgr logging | Lifecycle/errors only; no candidate result logging |
| Log-level control | XML debug levels and internal setter exist; do not change; no hidden match trace to enable |
| Port 5000 role | Unknown; not statically proven ScreenSession or diagnostics |
| Port 5000 read-only diagnostic | Unknown, no structured command protocol proven |
| Binder/dumpsys | General JMediaCore Binder/IPC support; devmgr dump unsupported by evidence |
| Local IPC diagnostic | MediaCore operation IPC exists; no devmgr listing operation found |
| Signal dump | None found; signal wait controls normal shutdown |
| Existing client | None identified in selected forensic extraction/static code search |
| Safe pre-existing diagnostic | **NO** |
| Car needed | **NO** for this offline conclusion |

## Least-invasive escalation comparison (not executed)

Ranking considers only vehicle modification, process disruption, persistence, crash risk, and amount of data needed.

| Rank | Option | Vehicle modification | Process disruption | Persistence | Crash risk | Data needed |
|---:|---|---|---|---|---|---|
| 1 | A. A ptrace-capable read-only memory reader | None if host-side access only | Low to moderate: attach/stop behavior depends on mechanism | None | Low to moderate if strictly bounded and resumed correctly | Small: `mc_devs` cell, manager/list pointers, candidate nodes/interface words, callback addresses; capture during attach if match results themselves are needed |
| 2 | B. Temporarily attach a debugger and read only manager/list memory | None | Moderate: debugger attach commonly stops the target | None | Moderate | Same small pointer set; symbols resolve statically |
| 3 | C. Instrument/patch logging | Yes: modifies executable or loaded code/config | Moderate to high, likely restart/reload | Potentially persistent until restored | High relative to read-only observation | Code path and candidate state; more setup and validation than pointer capture |
| 4 | D. Other evidence-supported method | No known method found in current artifacts | Unknown | Unknown | Unknown | No specific supported alternative established |

Options A/B still require a separately designed parked-session procedure and explicit review before execution. Do not connect the iPhone or attempt access via port 5000 as part of this static milestone.

## Evidence links

- [jmcs diagnostic audit](../research/carplay/jmcs-diagnostics.md)
- [Port 5000 static audit](../research/carplay/port-5000.md)
- [Runtime registry evidence](../research/carplay/runtime-device-registry.md)
- [Device registration](../research/carplay/device-registration.md)
