# SuperSU `su -c` execution path — Step 40E4 static branch A

## Scope and decision

Offline analysis of the archived `/system/xbin/su` only. The binary was not executed or emulated; no vehicle or ADB was accessed; the archive was not mounted. This is a static capability/behavior analysis, not a complete decompilation.

**`su -c` zero-persistent-write: NOT PROVEN.** The exact control flow from CLI parse through IPC, policy decision, logging, credential transition, command exec, and cleanup could not be recovered completely from this stripped ARM ELF with the available symbol/disassembly setup. Imports and strings prove capabilities and code fingerprints, not that each path is reached by one ordinary command. The safe conclusion remains to abandon `su` as a privileged collector mechanism unless affirmative, binary-matched evidence becomes available.

## Identity and provenance

| Property | Finding | Evidence class |
|---|---|---|
| SHA-256 | `d95fdbb551aca66d8a81471ea7683f58dba75a09d5cdc4712209b955574eab26` | Honda-archive confirmed; recalculated from extracted archive member |
| Size / archive metadata | 75,348 bytes; uid/gid 0:0; mode `06777` | Honda-archive confirmed; repeated in dated full-system archives per Step 40E3 |
| ELF | ELF32, little-endian, ET_DYN, ARM, EABI5 | Honda-archive confirmed |
| Entry / interpreter | ELF entry `0x3528`; `/system/bin/linker` | Honda-archive confirmed |
| Dependencies | `libdl.so`, `libstdc++.so`, `libm.so`, `libc.so` | Honda-archive confirmed from dynamic table |
| Build marker | `2.77:SUPERSU`, Chainfire copyright; GCC 4.8/4.9 markers | Honda-archive confirmed; identifies family/version marker, not exact upstream build |
| Exact upstream match | Not established | No hash-matched upstream ARM binary acquired |

Chainfire's official v2.77 release information and How-To are comparison references only: [v2.77 release](https://chainfire.eu/articles/950/SuperSU_v2.77_BETA_-_Note7_Exynos_shenanigans), [How-To SU](https://su.chainfire.eu/). The release archive URL did not yield a comparable executable in the earlier acquisition attempt. Public `libsuperuser` is a caller-side library, not the proprietary `su` implementation.

## CLI and execution fingerprints

The archived `.rodata` includes:

- `Usage: su [options] [--] [-] [LOGIN] [--] [args...]`
- `-c, --command COMMAND pass COMMAND to the invoked shell`
- `Usage#2: su LOGIN COMMAND...`
- daemon/reload forms `-d|--daemon`, `-ad|--auto-daemon`, `-r|--reload`
- install/uninstall forms and `--id pid`
- shell, login, preserve-environment, context, mount-master/namespace options
- `SHELL`, `HOME`, `USER`, `LOGNAME`, `PATH`, `LD_LIBRARY_PATH`, `ANDROID_PROPERTY_WORKSPACE`

The usage text also states auto-daemon behavior is SDK-dependent (starts automatically on SDK >=18 or under another condition not recovered). The target is API 17. This does not prove whether the API17 invocation contacts, launches, or initializes a daemon.

Imports show the executable contains code paths capable of using `fork`, `execve`, `execv`, `execle`, `execl`, `waitpid`, `pipe`, `socketpair`, `socket`, `connect`, `bind`, `listen`, `accept`, `sendmsg`, `recvmsg`, `poll`, `select`, and `ioctl`. This is consistent with client/daemon and command execution behavior. Exact per-invocation path and IPC endpoint selection are not proven.

Historical session evidence records `su -c id` returning uid 0. That proves this command form worked in that prior state; it does not establish current daemon state, policy/logging settings, or zero-write behavior.

## Persistent-state and privilege capabilities

The dynamic import table contains the following write-capable calls (exact reachability for the normal `su -c <command>` path is unknown):

| Capability | Imports / strings | Specific invocation result |
|---|---|---|
| File creation/read/write | `open`, `fopen`, `write`, `read`, `fclose`, `lseek`, `mkdir`, `unlink`; no imported `openat`, `creat`, `truncate`, `rename`, `fsync`, or SQLite API | Unknown; open flags and actual paths on the normal command path have not been resolved |
| Ownership/mode | `chmod`, `fchmod`, `chown`, `fchown`, `umask` | Unknown reachability; strings include `chmod` and install/maintenance paths |
| Mount/policy | `mount`, `ioctl`, `dlopen`, `dlsym`; strings include `supolicy`, `supolicy.loaded`, mount namespace, and SELinux contexts | Unknown reachability; installation/daemon paths may use these |
| Property | imported `__system_property_get`; string `/data/property/persist.sys.root_access` | Read capability confirmed; no property-write import identified in dynamic symbols, but indirect/dynamic mechanisms are not excluded |
| Credentials/capabilities | `setuid`, `setreuid`, `setresuid`, `setgid`, `setregid`, `setresgid`, `setgroups`, `capget` | Capability confirmed; exact credential sequence and child state are unknown |
| Logs/config/requests | strings for `/data/data/eu.chainfire.supersu/files/supersu.cfg`, `.../logs/`, `.../requests/`, `.../connections/`; config keys `nodefaultcontentlog`, `logsize`, `forceshell` | Paths/config fingerprints confirmed; flags, writes, and whether touched by a simple command are unknown |
| Daemon/install | `/system/xbin/daemonsu --auto-daemon &`, `/su/bin/daemonsu`, `/system/xbin/daemonsu`, `install-recovery.sh`, `su.d` scripts | Capability and path fingerprints confirmed; exact conditions and startup effects unknown |

`nodefaultcontentlog` is evidence that content logging has a configurable dimension in this build family. It is not evidence that logging is disabled in this archive, nor that disabling content logging disables request/policy/connection bookkeeping. No captured matching config file or state was found in the inspected archive set that proves logging off.

## CLI-to-command control-flow status

Requested path: `su -c "<read-only collector command>"`.

| Stage | Result |
|---|---|
| ELF entry | Entry `0x3528`; startup code is present and dynamically links through Android linker. |
| Argument dispatch | Option/help strings prove `-c`/`--command` is supported. Stripped code does not expose named parser symbols. Full branch-level parse path not reconstructed. |
| Client initialization | Socket/IPC and daemon strings/imports show relevant code exists. Client initialization and daemon discovery call sequence not reconstructed. |
| Daemon absent/present | Both daemon and startup/install strings exist. It is unknown whether an API17 ordinary `su -c` starts one, whether startup persists state, or whether daemon state is assumed. |
| Policy lookup / prompt | Request/config/application paths and daemon linkage imply authorization handling; exact policy lookup, expired/missing policy behavior, and durable decisions not reconstructed. |
| Logging | Config strings and log directory prove logging support/configuration fingerprints. Unconditional vs conditional behavior for this invocation unknown. |
| Credential transition | UID/GID/group/capability APIs imported. Exact order and values unknown. |
| Shell/command exec | `-c` help text says command is passed to invoked shell; exec APIs imported. Exact shell selection/quoting/environment and child setup unknown. |
| Cleanup | `waitpid`, signals, socket and file APIs exist. Normal-path cleanup effects unknown. |

A best-effort disassembly was produced with Apple `objdump` and Python `pyelftools`/Capstone in `/tmp`; stripped function boundaries and mixed ARM/Thumb decoding made it insufficient to safely claim exact control-flow edges or call-site arguments. These temporary analysis dependencies were outside the repository. No binary execution or emulation occurred.

## Daemon and policy conclusions

- **Daemon-already-running branch:** plausible from daemon/client strings and socket APIs, but no exact IPC path or files touched was proven.
- **Daemon-not-running branch:** the binary contains auto-daemon and helper-path strings, and API-gated auto-start text; whether a simple command starts it on this Android 4.2.2/API17 unit is unknown.
- **Existing allow policy:** historical successful root command suggests some previously usable grant path, but does not identify stored policy or current state.
- **No/expired policy or interactive prompt:** request directory and SuperSU app paths exist as strings; exact behavior and writes unknown.
- **Missing SuperSU app state:** archives inspected in Step 40E3 lacked the companion APK/app-data and standalone `daemonsu`, `supolicy`, `sugote` files. A missing companion may change failure/initialization behavior; no safe inference can be made.
- **One-shot no-log/no-persist mode:** not found/proven. `nodefaultcontentlog` is an internal config key, not a verified safe CLI switch. No undocumented option should be inferred from it.

## Decision

**Do not use archived `su` for Step 40F.** An invocation might only create transient RAM/IPC state in one existing-daemon configuration, but the exact configuration cannot be established statically from these archives. Other reachable branches include logging, requests, daemon startup and installation maintenance. Without complete matched-binary control flow plus proven runtime config/daemon state, the privilege mechanism cannot be justified as zero-persistent-write.

### Review packet facts

- Binary hash: `d95fdbb551aca66d8a81471ea7683f58dba75a09d5cdc4712209b955574eab26`.
- Version marker: `2.77:SUPERSU`; ARM32 EABI5; dynamic Android ELF.
- High-priority unresolved facts: exact branch edges/call arguments from `-c`; open flags for SuperSU log/request/config/connection files; daemon absent/present behavior on API17; policy write behavior; current logging configuration.
- Proposed future command, if separately approved after proof: `su -c "cat /proc/<pid>/maps"` (placeholder only; not run and not authorized). It is not considered zero-write because pre-command setup, policy, daemon, and logging behavior remain unknown.
- Assumptions: archive content reflects a historical modified unit; no current target state is inferred.
- No independent review was performed in this branch.
