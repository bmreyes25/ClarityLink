# No-`su` privileged-read alternatives (Step 40E4)

## Result

The preserved system has **no approved zero-persistent-write privileged read path established by this audit**. The strongest concrete lead is Android's root-owned `dumpstate` service, invoked by the unprivileged `bugreport` wrapper over an init-created local socket. Its fixed diagnostic collection includes a `SMAPS OF ALL PROCESSES` section and related process data. However, the service is broad, may signal processes to collect stacks, and the binary contains filesystem-write operations. Its exact conditional write path and effects of `dumpstate -s` were not proven absent. It is therefore an investigative candidate, **not a safe or approved substitute** for the narrow collector.

No archived binary or APK was executed. Source archives were read as tar members; this document is a static capability assessment, not runtime validation.

## Candidate: init `dumpstate` service via `bugreport`

Evidence from `root-startup.tar`:

```text
service dumpstate /system/bin/dumpstate -s
    class main
    socket dumpstate stream 0660 shell log
    disabled
    oneshot
```

The service has no `user` override, so it runs with init's default service credentials (root on this Android init model). Its local stream socket grants the `shell` group access while the service is running. Because it is `disabled`, it is not automatically started with its class; the archive does not establish socket availability outside service activation.

The archived `/system/bin/bugreport` is root-owned mode `0755`, group `shell`, 5,368 bytes. Static strings/imports include `property_set`, `socket_local_client`, `ctl.start`, `dumpstate`, and `Failed to connect to dumpstate service`. This strongly fingerprints a shell-callable wrapper that requests the init `dumpstate` service and connects to it. No exact disassembly/control-flow proof was obtained; describe the wrapper's activation sequence as **high-confidence static inference**, not a reconstructed instruction trace.

The archived `/system/bin/dumpstate` is root-owned mode `0755`, group `shell`, 42,300 bytes. Its usage strings state `-s: write output to control socket (for init)` and embedded section labels include `PROCESSES AND THREADS`, `LIST OF OPEN FILES`, `SMAPS OF ALL PROCESSES`, and `BLOCKED PROCESS WAIT-CHANNELS`. Other strings include `/proc/%d/exe`, `/proc/%d/wchan`, `SHOW MAP`, process timeouts, `kill(%d, SIGQUIT)`, `mkdir(%s)`, and `fchmod on %s failed`. This proves the binary contains those diagnostic features/paths, but not that every one runs on the `-s` service path or that it yields complete `jmcs` maps/smaps in this build.

| Question | Assessment |
|---|---|
| Can ordinary shell ask init to start a root diagnostic process? | **Likely yes:** wrapper strings and service/socket configuration fit this path. Not dynamically tested. |
| Can it return useful target proc information? | **Potentially:** dumpstate has all-process smaps, process, and FD section labels. Completeness for `jmcs`, page-size extraction, and exact output format are unverified. |
| Is it a narrow read-only proxy? | **No:** it collects broad system diagnostics and logs. |
| Can it signal or perturb other processes? | **Yes, potential confirmed by binary string:** SIGQUIT path exists for thread/VM trace capture; reachability/condition on `-s` was not established. |
| Can it write persistent files? | **Potentially:** `mkdir`/`fchmod` and output-file options are present. The exact service path and destination conditions were not reconstructed, so zero-write is not proven. |
| Can this be used in Step 40F-Lite now? | **No:** it is a root service triggered by a shell wrapper, broad, and insufficiently characterized. Do not execute it as part of this milestone. |

This candidate is worth retaining as the single best alternative if later static analysis of the exact archived `dumpstate` source/disassembly can establish that the socket mode avoids signals and persistent output. Even if safe, it would produce a large sensitive bugreport and require strict host-side filtering; it would not be equivalent to a small path allowlist.

## Root-owned services and local IPC

| Candidate | Archive evidence | Why it is not an approved target-process read proxy |
|---|---|---|
| `prop_daemon` | `init.vcm30t30.rc` starts `/system/bin/prop_daemon` as root. Binary strings include `/dev/socket/PropDaemon_MsgSend`, `property_set`, and `set_android_property`. | This is a property-control interface, not a `/proc/<pid>` read service. It is state-changing by design. Socket mode/authentication and wire protocol are not established. Do not connect to it. |
| `diag_daemon` | Init starts `/system/vendor/bin/diag_daemon` as root, group `root vehicle_rw`. Binary strings include `socket_local_server`, `readDspMem`, `writeDspMem`, `/proc/sys/kernel/printk`, `procfs read`, and `/dev/block/mmcblk0`. | Diagnostic socket protocol/authentication is unknown. It includes DSP writes and block-device references, so it is outside a read-only collector even if some read operations exist. No arbitrary target proc maps/smaps API is proven. |
| `inlinediag` | Init defines `/vendor/bin/inlinediag` as root, `disabled`, `oneshot`. Strings show Binder interfaces, `diag_daemon`, logcat, and writes/chmod/chown under `/data/data/inlinediag`. | Diagnostic app/service, not a narrow shell proc proxy; may alter logs/permissions/files, and its exact interface is not a supported generic proc read API. |
| `devproxy` | Init defines `/system/bin/devproxy` as root, `disabled`, `oneshot`. Binary strings identify TI GNSS `dproxy`/AI2 processing and log read/write paths. | Specialized GNSS proxy, no evidence for process maps/smaps/FDs; its purpose and file/log paths are unrelated. Do not start it. |
| `disp_com_cid`, `disp_com_meter`, `jmcs` | Init starts or defines root services for display/MediaCore. | These are system functions, not shell-exposed proc readers. No appropriate request API is established; attaching to or modifying them is explicitly out of scope. |
| `dumpstate` | Described above. | Broad diagnostic proxy candidate with possible process signals and filesystem side effects; not presently safe. |

`init.rc` also defines system services such as servicemanager, vold, netd, debuggerd, and keystore. Their existence does not provide a shell-authenticated arbitrary `/proc` read interface. Android Binder access is permission/interface-specific; no archive evidence shows an exposed service that returns arbitrary target maps/smaps/fd data to shell.

## SUID/SGID inventory relevant to reads

Metadata below comes from `tar -tvf system-vendor.tar` (the archive member set has both `system/...` and `data/...`; the listed paths are the `system` members). The list is limited to special-bit executables relevant to shell privilege or diagnostic access.

| Path | Owner:group / mode | Interface/purpose evidence | Can supply denied `jmcs` maps/smaps/fd? | Side effect/safety result |
|---|---|---|---|---|
| `/system/xbin/su` | `0:0`, `06777` | SuperSU `-c` client, covered by Step 40E3. | Arbitrary command can read only after privilege escalation. | **Rejected:** mode is unsafe and `su -c` zero-write is unproven. |
| `/system/bin/run-as` | `0:2000`, `06750` | Strings: `run-as <package-name> <command>`, only shell/root callers, rejects packages not debuggable. | No. It transitions into an app UID/package context, not a root proc reader; package ownership cannot read root-owned `jmcs` proc entries. | Not a root shell. No target writes required to establish this conclusion. |
| `/system/vendor/bin/susetprop` | `0:1900`, `04750` | Strings: `susetprop <key> <value>`, calls `__system_property_set`. Shell is not group 1900 per recorded UID/groups. | No; sets properties, no arbitrary file read interface. | Property mutation by purpose; group gate prevents ordinary shell use in the observed account. |
| `/system/bin/dmesg` | `0:1000`, `04750` | Special-permission diagnostic tool. | No; kernel log is not target `/proc` mappings. | May expose logs; no `/proc` proxy. Shell group membership/read access to dmesg is not established here. |
| `/system/vendor/bin/diag_daemon` | `0:2000`, `0755` (not SUID) | Root init service, diagnostic local socket, DSP and block-device functionality (above). | Not proven; service API is unknown. | Exclude because interface includes write-capable diagnostics and block-device references. |
| `/system/bin/dumpstate` | `0:2000`, `0755` (not SUID) | Root init service with shell-group control socket, all-process diagnostic strings (above). | Potentially broad smaps/process output, not established as complete or safely callable. | Do not execute until signal/write path is proven safe. |

Other archived special-bit members are network/vehicle utilities (`netcfg`, `ping`, `pppd`, `rfcomm`, `emgsetdns`, `mcreset`, `menucolor`, `calibrator`, `init_ppp_files.sh`). Metadata does not show a plausible shell-accessible arbitrary target-proc reader; some perform networking, vehicle configuration, calibration, or filesystem changes and are out of scope. The shell's supplemental groups do not include the archived privileged helper groups `1900`, `1000`, `3003`, or `3004` in the previously recorded `id` evidence, except `log`, `graphics`, `input`, `adb`, and networking groups.

## No-su decision tree

```text
Need root-only jmcs proc evidence
  ├─ adbd already root without state change?  No: recorded shell UID 2000;
  │                                         archived production defaults secure=1/debuggable=0.
  ├─ exposed root read-only proxy?             No confirmed proxy.
  │   └─ dumpstate/bugreport candidate?         Yes, but broad; signals and writes unexcluded.
  ├─ SUID/SGID helper that reads arbitrary proc? None identified.
  └─ result                                   No justifiable zero-write privileged path now.
```

**Recommended disposition:** abandon `su` as the presumed necessary mechanism; do not start any root service. Continue with already captured unprivileged data and offline analysis. Preserve `dumpstate` as one narrowly defined static-analysis follow-up only if closing its `-s` signal/write behavior is likely to change the Step 40F decision. Do not let this candidate become permission to run a bugreport.

## Evidence limits

- Archive files are static snapshots of a modified unit; current service state/socket permissions are not known.
- String presence is not proof of call reachability, exact arguments, or condition on a particular init service path.
- `dumpstate` and `bugreport` were not disassembled because this offline pass did not have an ARM-capable disassembler available; neither was executed.
- Socket modes shown in init configuration do not prove a socket exists while its `disabled` service is stopped.
- The only direct observed access result remains prior capture evidence: shell UID 2000 was denied `jmcs` maps, smaps, and fd. No new live access check was performed.
