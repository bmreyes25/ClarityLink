# Step 40E4 privilege-acquisition threat model

## Scope and zero-write definition

This review concerns only obtaining the Step 40F runtime reads. **Zero-persistent-write** means the privilege-acquisition mechanism does not intentionally create, modify, truncate, rename, unlink, chmod, chown, relabel, update, or persist data in a filesystem or block device. RAM-only process state, anonymous mappings, pipes, Unix sockets, Binder messages, and kernel bookkeeping are recorded separately. Reads can still cause filesystem atime updates; that metadata possibility is distinct from an application-generated write. A path is not called zero-write merely because its requested command is `cat`.

No live `su`, HondaHack, ADB, or archived ARM executable was run for this review. No target filesystem was mounted or modified.

## Threat table

| Effect | Possible on candidate path? | Persistent? | Proven for one `su -c cat`? | Mitigation / disposition |
|---|---|---|---|---|
| SuperSU request or command log | Binary strings include SuperSU log/request paths; official docs describe optional command-content logging | Potentially | No | Do not assume logging is disabled. No one-shot no-log mode established. |
| SuperSU policy/history/config update | Policy/config path strings and daemon architecture are present | Potentially | No | Archived configuration does not prove current policy nor request outcome. Avoid the transaction. |
| Daemon initialization/start | SuperSU strings/imports refer to daemon and helper paths | Potentially; files/socket state may persist | No | Running-daemon and absent-daemon branches are not fully reconstructed; cannot assume daemon already exists. |
| Android/system logging | HondaHack code explicitly removes SuperSU log files in its own runner; this is not evidence every `su` invocation writes logs | Potentially | No | Never use HondaHack as a wrapper; deleting logs afterward is itself a write and does not erase prior side effects. |
| atime from archive/proc reads | Captured `/proc` mount was `rw,relatime`; other mount details vary | Filesystem metadata may persist | No per-path proof | Distinguish read-induced metadata from privilege mechanism writes; exact target mount/options unavailable for a future session. |
| Temporary file or database write | File/database-related strings and write-capable imports exist | Potentially | No callsite-to-command reachability proof | Static path must be affirmatively excluded before approval. |
| Property or mount change | HondaHack contains commands that set persistent properties and remount `/system` RW | Yes | Not attributed to plain `su -c` | Do not invoke HondaHack's feature runner or install/startup flow. |
| Permission/ownership/SELinux change | `su` has relevant imports/strings; exact path unknown | Potentially | No | No mode changes, policy installs, or `supolicy` operations allowed. |
| Process signal / stop | `su` imports process/signal APIs; collector itself does not request signals | Usually transient, but can disrupt session | No invocation-specific path proof | Prohibited for Step 40E4/40F. |
| Target process pause | Not part of fixed-read collector; procfs reads alone do not request a stop | Transient | Not applicable | No ptrace, attach, or stop operations. |
| Reboot requirement | ADB-root/property enablement and init changes in HondaHack can require persistent configuration/restart | Yes | Not part of plain `su -c` proof | No root enablement, property changes, reboot, or service restart. |
| Collector host output | Step 40F writes a private capture bundle on the host | Persistent on host, not target | Yes by design | Outside-repository destination, restrictive modes, bounded files; this is not zero-write overall, only zero-target-write. |

## Decision

The available static evidence does not prove the exact `su -c` request is free of persistent writes. The archived `su` also has group/other write permissions (`06777`), and there is no pristine factory image to establish its origin. Thus the proposed privileged route is not justifiable as zero-write. The independent no-`su` audit and Step 40F-lite matrix are in [alternative root paths](alternative-root-paths.md) and [collector privilege matrix](collector-privilege-matrix.md).

**Step 40F remains NOT READY.** Do not weaken the zero-write definition or use log deletion as mitigation. If no existing read-only proxy is found, continue only with evidence already captured or with ordinary unprivileged reads that add material information.
