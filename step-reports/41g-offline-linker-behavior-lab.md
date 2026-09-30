# Step 41G — Offline linker behavior lab or seam decision

**Decision: an offline Honda linker lab cannot be safely/reliably run with the tools and guest artifacts present. The bounded static pass did not resolve Honda preload behavior. Downgrade `LD_PRELOAD` from a plausible path to an UNKNOWN, parked candidate; do not run Step 42.**

No vehicle, ADB, jmcs execution, boot/recovery modification, partition mount/write, library staging, or Type111 activity occurred. No synthetic test binaries were built or executed because there is no compatible user-mode runner or offline guest environment.

## Part 1 — Lab feasibility

| Item | Local state |
|---|---|
| `qemu-arm` / `qemu-arm-static` | Not installed / not on PATH |
| Container runtime (`docker`, `podman`, `nerdctl`) | Not installed / not on PATH |
| QEMU | Homebrew QEMU 11.1.2 includes `qemu-system-arm`, but no user-mode ARM emulator |
| UTM | App installed; no local `.utm`, qcow2, ARM Linux kernel, or root filesystem was found in searched user/workspace locations |
| ARM Linux/Android guest | Not available locally |
| `capstone`, `pyelftools` | Available from repository-local `research/tools/python`; used for static inspection only |

`qemu-system-arm` requires an ARM guest kernel and a guest root filesystem. Neither is available. Booting Honda's captured boot image/root filesystem would execute a broader proprietary environment, not the permitted synthetic binaries and linker-only lab, and could start forbidden services. Installing/download-fetching tools or guest images would violate the offline-only constraint. Therefore:

```text
OFFLINE LINKER LAB: NOT POSSIBLE
REASON: no QEMU user-mode runner/container or pre-existing isolated ARM guest; system emulator alone is insufficient
```

## Part 9 — Bounded static control-flow attempt

The temporary Honda linker copy from Step 41F was re-hashed: `608af427ac43a316471e5adc18e25f6d3c9ac5e4ec2c04f19561ee774357aa90`. It is ELF32 ARM `ET_DYN`, entry `0x3220`; jmcs's recorded interpreter is `/system/bin/linker`. `llvm-objdump` and Capstone static decoding were available. Existing names/data include `LD_PRELOAD` at VA `0xc7fc`, `LD_LIBRARY_PATH` at `0xc7ec`, `CANNOT LINK EXECUTABLE`, the generic load-library error, `/vendor/lib`, `/system/lib`, plus `getenv`, `getuid`, `geteuid`, `getgid`, and `getegid` symbols/functions. The path/env string pointers reside in `.data.rel.ro.local`.

The targeted direct-branch scan did not recover a direct `BL`/`BLX` reference to the linker `getenv` or UID/GID helper entry points. That is not proof they are unused: stripped ARM/Thumb code can inspect `envp` inline, call indirectly, or reach code outside the decoded range. No reliable xref/dataflow from the `LD_PRELOAD` string/pointer through a parser, secure-mode branch, `open_library`, and the main executable failure path was established. No `AT_SECURE` string was found, which is not proof its numeric auxv tag is absent.

| Requested behavior | Result |
|---|---|
| Does Honda linker call `getenv("LD_PRELOAD")`? | No direct call found in the bounded branch scan; semantic environment handling UNKNOWN |
| Does the value flow into a parser? | UNKNOWN |
| Space/colon separators, entry/buffer limits | UNKNOWN |
| `name[0] == '/'` direct open branch | UNKNOWN |
| Failed preload becomes fatal | UNKNOWN |
| Secure branch skips preload | UNKNOWN |

No further static reverse engineering is justified in this step without a source-identified Honda build or stronger symbols/relocation/debug evidence. The task's decisive lab path is unavailable in the current offline workspace.

## Secure-exec and data mapping reassessment

jmcs is mode 0755, owner 0/group 2000, has no observed set-ID bits or extended attributes, and its init stanza selects root:root. A normal credential transition therefore suggests `AT_SECURE` would be false; Honda's secure-mode implementation and any LSM decision remain unknown. Do not treat that expectation as a confirmed linker result.

Historical capture `research/captures/20260925T150706Z-capabilities/capability-survey/cat-_proc_mounts.txt` records `/data` mounted `rw,nosuid,nodev` without `noexec`. `DATA_NOEXEC: NO` applies to that capture. `/data/local/tmp` exists mode 0771 shell:shell; root DAC traversal is plausible. Actual executable mapping is still not proven because SELinux/domain and kernel mmap enforcement are unknown. Mapping risk remains **MEDIUM**.

## Seam decision and next study

`LD_PRELOAD` is **UNKNOWN** as a Honda behavior, not confirmed supported and not disproven. Keep it as a parked hypothesis only. Do not rank it as the active next path: a missing/invalid preload may prevent jmcs startup if Honda follows the AOSP model, and rollback/recovery has not been tested.

The next seam to study offline is Honda's existing **ExternalDisplay/CarPlayService companion path**: map its Java/native/Binder APIs and determine whether a separate Honda-managed service could receive or route an additional authenticated video stream without changing jmcs. Existing project evidence calls ExternalDisplay a likely secondary render host, but no Type111 ingestion/receiver equivalent is proven. This is a research candidate, not a deployable alternative. If it cannot own the CarPlay negotiation/stream path, the remaining architectural alternative is a non-injected external receiver/proxy design, which requires separate security/session-crypto feasibility analysis.

| Candidate | Avoids loading code into jmcs? | Existing evidence | Assessment |
|---|---|---|---|
| Stock jmcs wrapper launcher | No; `exec` alone does not interpose internal jmcs calls | Needs service command/ramdisk change; preload behavior remains same if it sets LD_PRELOAD | Does not bypass blocker |
| Init service wrapper | No, unless it replaces jmcs behavior | Persistent boot change and additional failure surface | Not preferred |
| Binder/service companion | Yes | Honda local services exist, but no SETUP/Type111 handoff contract is established | Study only |
| ExternalDisplay companion | Yes for output process | Honda ExternalDisplay View host is a likely render target; receiver ownership unknown | **Next study candidate** |
| Pure offline Type111 receiver model | Yes | Existing static protocol model possible | Useful research, not a deployment/load seam |
| Network-side proxy | Potentially | Session negotiation/security material and port ownership not solved | High complexity; defer |

## Decision gate

```text
OFFLINE LINKER LAB: NOT POSSIBLE
HONDA LINKER LD_PRELOAD: UNKNOWN
ABSOLUTE LD_PRELOAD PATH: UNKNOWN
LD_PRELOAD SEPARATORS: UNKNOWN
CONSTRUCTOR ORDER: UNKNOWN
MISSING PRELOAD FATAL: UNKNOWN
INVALID PRELOAD FATAL: UNKNOWN
AT_SECURE HANDLING: UNKNOWN
LD_PRELOAD SUPPRESSED FOR JMCS: UNKNOWN
DATA NOEXEC: NO (historical capture)
/data/local/tmp MAPPING RISK: MEDIUM
LD_PRELOAD SEAM STATUS: UNKNOWN
BOOT RAMDISK CHANGE REQUIRED: YES
NO-OP LOAD TEST: NOT READY
TYPE111 LIVE WORK: NOT READY
NEXT SEAM IF NOT LDPRELOAD: Offline ExternalDisplay/CarPlayService companion API and stream-ownership audit
BIGGEST BLOCKER: no isolated ARM user-mode/guest environment, and Honda linker behavior remains unresolved without it
```

## Validation

This report was followed by a synthetic probe build; see [Step 41G runtime probe](41g-runtime-preload-probe.md). No temporary Honda binary or generated ARM test binary is committed. Temporary linker and init copies used for static inspection were deleted. `git diff --check` applies to the combined follow-up.
