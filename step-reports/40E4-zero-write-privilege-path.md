# Step 40E4 — Zero-write privilege path decision

**Status: OFFLINE AUDIT COMPLETE; no justifiable privileged read path found.** No vehicle or ADB access occurred. No archived ARM executable or APK was run or emulated. No source image was mounted read-write; no firmware, target, block image, or permission was changed. The Step 40F privileged collector remains disabled.

## Decision

The required exit outcome is **NO JUSTIFIABLE PRIVILEGED PATH**. The archived SuperSU 2.77-family `su -c` path could not be proven zero-persistent-write. Archived production-style ADB configuration and observed UID 2000 do not establish root-capable `adbd`. No other narrow root read proxy was found. `dumpstate` is a plausible source of broad proc diagnostics but may signal processes and write output; its service path is not sufficiently characterized and it is not approved.

The useful unprivileged capture already exists: Step 40E collected three phases and demonstrated availability of process/thread metadata, masks, display diagnostics, bounded logs, platform data, and global `/proc/net`. It was denied `/proc/<jmcs>/maps`, `smaps`, and `fd`. A second Lite vehicle session would duplicate evidence and would not close that gap.

## SuperSU finding

Archived `/system/xbin/su` SHA-256 is `d95fdbb551aca66d8a81471ea7683f58dba75a09d5cdc4712209b955574eab26`; it is ELF32 LE ARM EABI5, ET_DYN, dynamically linked through `/system/bin/linker`, and bears `2.77:SUPERSU` / Chainfire markers. The bytes and `06777` mode match three preserved full-system captures of the already-modified unit; they do not establish factory provenance or who set the mode.

Strings identify `-c`, daemon/autodaemon, install/uninstall, config, request, log, connection, and helper paths. Imports expose file, ownership/mode, mount/ioctl, process/signal, IPC, and credential capabilities. These are not proof of the branch taken for one `su -c cat` request. The stripped binary did not permit reliable full branch reconstruction or recovery of file-open flags/callsite arguments with available static tooling. It has no proven one-shot no-log/no-persist mode. HondaHack independently uses `su`, deletes SuperSU logs, and performs persistent system modifications; deleting logs afterward does not make an invocation zero-write.

Details: [SuperSU execution path](../research/runtime/supersu-execution-path.md), [write-side-effect inventory](../research/runtime/supersu-write-side-effects.md), [Step 40E3 root-path report](../research/platform/honda-root-path.md).

## Alternative paths

- **`adbd` root without `su`: NO on archived configured evidence.** `ro.secure=1`, `ro.debuggable=0`, `user`/`release-keys`, and historical shell UID 2000 indicate no enabled root-shell path. Do not change properties or USB/init configuration.
- **Existing root read proxy: NO confirmed.** `dumpstate`/`bugreport` is a static lead only. Its broad diagnostics include all-process smaps strings and potential SIGQUIT, mkdir, and fchmod paths. Do not execute it.
- **SUID/SGID helpers: none identified that safely provides arbitrary target-proc reads.** `run-as` enters an app identity; `susetprop` mutates properties; `dmesg` is not a procfs proxy. Root diagnostic services have unsupported or write-capable interfaces.
- **40F-Lite: READY as an evidence profile and already completed in Step 40E.** No new code or vehicle session is justified. It does not unblock Step 41.

See [adbd model](../research/runtime/adbd-privilege-model.md), [alternative root paths](../research/runtime/alternative-root-paths.md), [collector privilege matrix](../research/runtime/collector-privilege-matrix.md), and [40F-Lite profile](../research/runtime/step40f-lite.md).

## Safety model and review

Zero-persistent-write means the privilege acquisition mechanism intentionally performs no filesystem/block-device create, modify, truncate, rename, unlink, chmod, chown, relabel, update, or persistence. RAM-only state, anonymous mappings, pipes, Unix sockets, Binder/kernel bookkeeping, tmpfs, and atime are tracked separately. This definition does not excuse an application write because a log may later be deleted.

ECC security-review workflow was applied. **Independent review: NOT PERFORMED.** A compact handoff is in [the review packet](../research/runtime/step40e4-review-packet.md). No code changed; no test suite was run. `git diff --check` is required and recorded after documentation assembly.

## Decision gate

```text
SUPERSU BUILD: Chainfire SuperSU 2.77-family; exact upstream binary match UNKNOWN
SU CLIENT PATH TRACED: PARTIAL
SU DAEMON PATH TRACED: PARTIAL
PERSISTENT WRITE SITES FOUND: write-capable imports/paths; exact su -c reachability and flags UNKNOWN
SU -C ZERO-PERSISTENT-WRITE: NOT PROVEN
SUPERSU LOGGING: CONDITIONAL / UNKNOWN for this invocation and archived configuration
SUPERSU POLICY UPDATE: CONDITIONAL / UNKNOWN
DAEMON START SIDE EFFECTS: UNKNOWN on API 17; daemon and auto-start paths present
ONE-SHOT NO-LOG MODE: NOT PROVEN
ADBD ROOT WITHOUT SU: NO on archived configured evidence
SAFE EXISTING ROOT READ PROXY: NO
MEANINGFUL UNPRIVILEGED 40F-LITE: YES; already captured as Step 40E
OFFLINE SUBSTITUTE FOR BLOCKED DATA: PARTIAL
ZERO-WRITE PRIVILEGED PATH: NO
STEP 40F: NOT READY
STEP 40F-LITE: READY / ALREADY COMPLETE
STEP 41: NOT READY
TYPE111 LIVE WORK: DISABLED
INDEPENDENT REVIEW: NOT PERFORMED
BIGGEST BLOCKER: no current-process maps/smaps source is both available and statically justified as zero-persistent-write
NEXT ACTION: decide whether Step 41 can be redesigned without current maps/smaps, or request independent static review of dumpstate's -s path without executing it
```
