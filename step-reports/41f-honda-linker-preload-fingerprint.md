# Step 41F — Honda linker preload fingerprint

> **Step 41G supersedes the Step 41F seam classification:** this fingerprint remains valid, but the seam is now UNKNOWN/parked because no isolated ARM lab was available and targeted static analysis did not resolve behavior.

**Result: Honda linker identity and preload-related data are confirmed; its exact preload control flow is not.** The `LD_PRELOAD` route remains plausible, but cannot be upgraded to PRIMARY or a no-op load test. Offline only: archived binaries were extracted to temporary scratch for static inspection, never executed; no vehicle, ADB, firmware/image write, partition mount, preload build, or deployment occurred.

## Honda artifacts and method

- `system-vendor.tar`, member `system/bin/linker`, SHA-256 `608af427ac43a316471e5adc18e25f6d3c9ac5e4ec2c04f19561ee774357aa90`. This matches the Honda linker identity recorded in Step 41B.
- `root-startup.tar`, member `init`, SHA-256 `db46c99b79e7f8ca7bafdb6f9017296272cd56a20be6f2d0deb9e4869ddb5c48`. Its strings include `selinux.`, `seclabel`, `setcon`, and `restorecon`. They support the presence of SELinux-related code paths, but do not establish `selinux_android_load_policy()` behavior or what init does when policy loading fails.
- ELF32, `EM_ARM`, `ET_DYN`, entry `0x3220`. Its executable `PT_LOAD` starts at file offset/VA 0, size `0xdd3c`; writable `PT_LOAD` has VA `0xfa38`, file offset `0xea38`, file size `0x7dc`.
- jmcs is the recorded ARM32 `ET_DYN` executable; its dynamic ELF interpreter is `/system/bin/linker` (see the Step 41B ELF record). The same path exists in APP as `/system/bin/linker`.
- `strings`, ELF section/dynamic-symbol inspection, `llvm-objdump`, and Capstone static disassembly were used. An exact Android 4.2 source tree was not present locally. Static disassembly did not establish the complete call/data flow from the preload string through secure-mode checks and load failure handling.

## Fingerprint observations

The Honda linker contains strings at these file/virtual offsets (the first load segment maps file offset to the same VA):

| String | File offset / VA | Observation |
|---|---:|---|
| `LD_PRELOAD` | `0xc7fc` | Present in `.rodata`; a data-table pointer to it is stored at VA `0xfa80` |
| `LD_LIBRARY_PATH` | `0xc7ec` | Present; data-table pointer at VA `0xfa78` |
| `CANNOT LINK EXECUTABLE` | `0xc81f` | Present |
| `could not load library "%s" needed by "%s"; caused by %s` | `0xc5c3` | Generic dependency load error present |
| `/vendor/lib` | `0xc837` | Present; pointer in `.data.rel.ro.local` at VA `0xfa38` |
| `/system/lib` | `0xc843` | Present; pointer at VA `0xfa3c` |

The dynamic symbol table contains `getuid`, `geteuid`, `getgid`, `getegid`, and `getenv` names; their presence alone does not prove an `AT_SECURE` check or fallback logic. No `AT_SECURE` printable string was found. The binary contains no source/build identity establishing an exact match to AOSP `android-4.2.2_r1.2` linker code. These are **fingerprints**, not behavioral proof.

## AOSP comparison checklist and Honda results

| Behavior | AOSP comparison supplied for this milestone | Honda archived-binary finding |
|---|---|---|
| `LD_PRELOAD` handling | AOSP 4.2 source has it | String and data pointer present; exact control flow UNKNOWN |
| Secure execution | AOSP checks `AT_SECURE`, then legacy ID mismatch if absent; suppresses/sanitizes environment in secure mode | Function names occur; `AT_SECURE` literal/string and branch not proven; UNKNOWN |
| Separators | AOSP parser uses space and colon | Honda parser separator and limits UNKNOWN |
| Absolute paths | AOSP attempts a leading-slash path directly | Honda branch/order UNKNOWN |
| Search order | AOSP checks preload path and configured/default directories | Default directory strings are present; order UNKNOWN |
| Preload error | AOSP preload failure aborts executable linking | Honda hard/soft failure behavior UNKNOWN; do not assume jmcs survives |
| Constructors | AOSP preload constructors run before main executable constructors | Honda constructor order UNKNOWN |
| Init `setenv` propagation | AOSP service environment is assembled before `execve` | Honda has parser diagnostic; service stanza supports no current `setenv`; Honda env propagation implementation not disassembled |
| SELinux load failure | AOSP `HAVE_SELINUX` path disables SELinux if policy load fails | Honda init contains SELinux-related strings (`selinux.`, `seclabel`, `setcon`, `restorecon`); policy load/failure path UNKNOWN |

This table deliberately keeps the supplied AOSP findings separate from Honda facts. A local AOSP source checkout was not found, and the milestone remains offline-only.

### Additional required checks

| Check | Honda result | Notes |
|---|---|---|
| `LD_PRELOAD` separators | UNKNOWN | Cannot establish space, colon, entry count, or buffer limits from the identified data strings |
| Missing preload fatal | UNKNOWN | AOSP comparison says fatal; Honda error string alone does not prove caller behavior |
| Bad-ABI preload fatal | UNKNOWN | Honda linker path not fully traced |
| Constructor crash/failure | UNKNOWN | Honda constructor/load order and error behavior not traced |
| Stock jmcs survives missing preload | UNKNOWN | If Honda follows the supplied AOSP model, it likely will not; this is not yet Honda-confirmed |
| Honda init disables SELinux after policy-load failure | UNKNOWN | No exact policy-load branch or failure fallback proved in archived `/init` |

## Secure execution expectation

The archived jmcs is mode 0755, owner 0/group 2000, with no observed setuid/setgid bits or extended attributes; init runs it as root:root. Ordinary exec credential rules therefore suggest no `AT_SECURE` trigger from set-ID/file capabilities. Expected `AT_SECURE` is **NO (inference)** for a root-to-root transition. Actual auxv/LSM behavior is not available, so actual state is **UNKNOWN**; `LD_PRELOAD` suppression for this jmcs launch is also **UNKNOWN**.

## `/data/local/tmp` access and mount flags

The saved historical `/proc/mounts` capture `research/captures/20260925T150706Z-capabilities/capability-survey/cat-_proc_mounts.txt` records:

```text
/dev/block/platform/sdhci-tegra.3/by-name/UDA /data ext4 rw,nosuid,nodev,noatime,user_xattr,barrier=1,journal_async_commit,nodelalloc,data=writeback,discard 0 0
```

For that captured runtime, `DATA_NOEXEC: NO`, `DATA_NOSUID: YES`, `DATA_NODEV: YES`. This is historical runtime evidence, not a guarantee for every boot. The archived init uses `mount_all /fstab.vcm30t30` and `mount_all /fstab.vcm30t30_post`; the fstab inputs were not recovered. The existing `/data` path, `/data/local`, and `/data/local/tmp` directory execute/traverse bits plus a root jmcs identity make ordinary DAC traversal plausible. A noexec flag was absent in the capture, but SELinux/process-domain and actual executable mmap remain unknown. Overall mapping risk: **MEDIUM**.

## Decision gate

```text
HONDA LINKER IDENTIFIED: YES
HONDA LINKER MATCHES AOSP 4.2 LD_PRELOAD PATH: PARTIAL
HONDA LINKER LD_PRELOAD: UNKNOWN
ABSOLUTE LD_PRELOAD PATH: UNKNOWN
LD_PRELOAD SEPARATORS: UNKNOWN
AT_SECURE CHECK: UNKNOWN
AT_SECURE EXPECTED FOR JMCS: NO (ordinary root-to-root inference; runtime unknown)
LD_PRELOAD SUPPRESSED FOR JMCS: UNKNOWN
MISSING PRELOAD FATAL: UNKNOWN
DATA NOEXEC: NO (historical mount capture)
/data/local/tmp MAPPING RISK: MEDIUM
BEST LOAD PATH: service-scoped LD_PRELOAD to a hash-pinned ARM library in /data/local/tmp (candidate only)
LD_PRELOAD SEAM STATUS: PLAUSIBLE_SECONDARY
BOOT RAMDISK CHANGE REQUIRED: YES
NO-OP LOAD TEST: NOT READY
TYPE111 LIVE WORK: NOT READY
BIGGEST BLOCKER: Honda linker secure-mode, absolute-path, and preload-failure control flow plus SELinux/executable-mmap access remain unproven
```

## Verification

`git diff --check` is the documentation gate. No code changed, so code tests do not apply. No target action or binary execution occurred.
