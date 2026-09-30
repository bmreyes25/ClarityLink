# SuperSU write-side-effects inventory — Step 40E4 static branch A

## Scope and write definition

This is an offline static inventory of the archived SuperSU-family `/system/xbin/su` (SHA-256 `d95fdbb551aca66d8a81471ea7683f58dba75a09d5cdc4712209b955574eab26`). The binary was not run or emulated. Here **zero-persistent-write** means that privilege acquisition does not intentionally create, modify, truncate, rename, unlink, chmod, chown, relabel, update, or persist data in filesystems or block devices. This distinguishes persistent application-generated writes from RAM-only process state, anonymous mappings, pipes, Unix sockets, Binder/kernel bookkeeping, tmpfs writes, and filesystem atime effects. Whether atime is persistent depends on mount/filesystem behavior and is not determined for the live unit by this binary analysis.

## Write-capable operation inventory

Imports and string references prove code capability/fingerprints, not a callsite's reachability from a plain `su -c <read>` invocation. Because exact branch/call argument recovery was not achieved, an unknown is deliberately retained rather than assigning a guessed target or flags.

| Operation / evidence | Target or target type | Persistent? | Reachable from ordinary `su -c`? | Can invocation disable it? | Evidence / limit |
|---|---|---|---|---|---|
| `open`, `fopen`, `write`, `fclose`, `mkdir`, `unlink` | SuperSU config `/data/data/eu.chainfire.supersu/files/supersu.cfg`; logs `/data/data/eu.chainfire.supersu/logs/`; requests `/data/data/eu.chainfire.supersu/requests/`; connections directories; other unknown paths | Potentially persistent on `/data` | Unknown | No verified one-shot switch | Imports and path strings; open flags/call edges unresolved |
| `chmod`, `fchmod`, `chown`, `fchown`, `umask` | Installation/helper paths and unknown files | Potentially persistent | Unknown; likely maintenance/install branch exists | Not established | Imports, `--install`/`--uninstall` strings, helper paths |
| `mount`, `ioctl` | Mount namespace/filesystem state | May alter kernel runtime state; mount changes can expose persistent filesystem state, not necessarily write file contents | Unknown | Not established | Imports plus mount-master/namespace strings |
| Dynamic loading (`dlopen`, `dlsym`) | `supolicy`/SELinux helper or other dynamically resolved operation | Unknown | Unknown | Not established | Imports and `supolicy` strings; indirect writes cannot be excluded |
| Property access | `/data/property/persist.sys.root_access` | A property update would be persistent | Read path indicated; write path not proven | Not established | `__system_property_get` imported; no direct property setter in dynamic imports, but indirect mechanisms remain possible |
| Policy/log bookkeeping via daemon IPC | SuperSU daemon state, request/access history, config/log/connection paths | Potentially persistent | A normal client/daemon path is plausible; exact reachability unknown | `nodefaultcontentlog` appears as a config key, but no verified no-persist mode | IPC and request/log/config strings; no exact source/binary-matched call trace |
| `exec*`, `fork`, `waitpid`, signals | Shell/child and helper processes | RAM/kernel state; child commands may have their own side effects | `-c` path supported, exact call chain incomplete | Not applicable | CLI help plus imports |

The dynamic symbol table does **not** import `openat`, `creat`, `truncate`, `ftruncate`, `rename`, `symlink`, `link`, `fsync`, `fdatasync`, or SQLite APIs. This is not a proof those effects are absent: wrappers may resolve dynamically, helpers/daemon may perform them, or operations may use other syscalls.

## Logging and policy

The archive strings include `nodefaultcontentlog`, `logsize`, `forceshell`, a SuperSU `logs/` directory, and a `requests/` directory. That proves configuration and storage concepts exist in the executable; it does not determine whether command content logging is enabled, whether a simple `su -c` creates a record, or whether a request/policy decision is persisted. The Step 40E3 archive review found no matching SuperSU app/config/data state sufficient to establish current policy/log settings.

HondaHack separately prepends a command that deletes SuperSU logs. This is evidence about HondaHack's behavior, not a no-log option in `su`. A write followed by deletion is not zero-write.

## Startup and installation effects

Strings identify `daemonsu`, `--auto-daemon`, `--daemon`, `--install`, `--uninstall`, `install-recovery.sh`, `su.d`, `/su/bin/daemonsu`, `/system/xbin/daemonsu`, and `supolicy`. This indicates daemon and maintenance/install code paths. Whether any are used before a regular `-c` command depends on target SDK/daemon/policy/config state and remains unknown. Usage text notes SDK-dependent daemon startup; on this API17 target, this still does not establish a no-start guarantee.

## Negative-search limits

No verified one-shot option was identified that disables both logs and policy/request persistence. The internal `nodefaultcontentlog` string is not a public/verified CLI flag. External Chainfire documentation describes optional content logging and daemon operation, but does not establish this unit's configuration or the effects of this exact binary. Exact upstream binary matching was not possible.

## Threat conclusion

| Threat | Possible from evidence? | Persistent? | Proven for simple `su -c`? | Mitigation |
|---|---|---|---|---|
| SuperSU log write | Yes; logs path/config strings | Yes if stored on `/data` | No; behavior unknown | Do not invoke `su` absent affirmative proof |
| Policy/request update | Yes; request/config/daemon path fingerprints | Yes if database/files are updated | No; behavior unknown | Do not invoke `su` |
| Daemon initialization/start | Yes; daemon paths and auto-start text | Possibly, depending on setup | No; behavior on API17 unknown | Do not invoke; avoid relying on assumed daemon state |
| Android logging | Possible through shell/helper or platform logging | Often persistent log buffers or files depending sink | Unknown | No safe invocation proof |
| Filesystem atime | Possible as a read side effect | May persist depending mount options | Not assessed for live target | Treat separately from intentional application writes; cannot certify here |
| Temp files | Possible through daemon/request/helper code | Depends on filesystem (`/data` vs tmpfs) | Unknown | Not proven absent |
| Property change | String indicates persistent root-access property read; direct setter not identified | Yes | Not proven | No property writes allowed |
| Mount change | `mount` imported; namespace features present | Runtime state; could expose persistent changes | Not proven | No mount operations allowed |
| Permission/ownership change | `chmod`, `chown`, `fchmod`, `fchown` imported | Yes | Not proven | No permission changes allowed |
| Process signal / target pause | signal/process APIs imported | Usually transient; target disruption possible | Not proven in normal command path | No signals/ptrace/stop permitted |

**Outcome: `su -c` zero-persistent-write is NOT PROVEN.** Given the task's exit rule, stop trying to certify it through open-ended static searching. Prefer ordinary unprivileged ADB evidence and offline substitutes; if a later privileged path is considered, require a separately bounded review and explicit authorization.
