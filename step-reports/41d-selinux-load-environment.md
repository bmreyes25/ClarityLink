# Step 41D / 41D2 / 41D3 — SELinux and jmcs load-environment audit

> **Step 41E update:** The archived Honda linker has `LD_PRELOAD`/loader strings and init has `setenv` parser evidence, but the linker's secure-exec branch, absolute path behavior, failure semantics, active SELinux state, and `/data/local/tmp` executable-map access are still unproven. Do not treat “no policy file found” as proof SELinux is disabled. See [Step 41E](41e-init-linker-preload-behavior.md). No-op load test remains NOT READY.

## Result

**Raw filesystem inspection complete; load-environment gate not passed.** All nine ext4 filesystems in the held raw eMMC image were inspected read-only with e2fsprogs `debugfs` 1.47.4. No named SELinux policy or context files were found. The exact Honda jmcs binary was identified in APP. The UDA filesystem contains `/data/local/tmp` as `/local/tmp`, mode 0771 and owner/group shell:shell, but no evidence establishes the active SELinux state/domain, `AT_SECURE`, or executable mapping permission. Step 42 is not ready.

## Work performed

- Committed the original Step 41D findings first as `a7cd616` (`ClarityLink: record blocked jmcs load-environment review`).
- Installed e2fsprogs 1.47.4 with Homebrew as explicitly allowed; used `debugfs` without `-w`.
- Read the GPT and ext4 superblocks from `../forensic/CLARITY_FORENSIC_WORKING/mmcblk0-full.img`.
- Copied one partition at a time to a temporary scratch directory so `debugfs` could access the partition image; deleted each temporary copy after use. No filesystem was mounted, and no journal replay, repair, or write command ran.
- Enumerated the top level of all nine ext4 partitions and recursively searched names for SELinux/policy/context, init rc, and fstab targets. No SELinux policy/context files were found. Broad `policy` substring hits were unrelated audio-policy files.
- Streamed APP `/bin/jmcs` through SHA-256 without saving a binary copy; it matches the archived Honda jmcs hash exactly.
- Read jmcs/linker and candidate directory metadata/xattrs. No extended attributes were returned for jmcs, linker, UDA `/local`, or UDA `/local/tmp`.
- Searched boot/recovery ramdisk findings and printable strings in held USP/whole-device MTD artifacts. No named policy/context artifact was found; embedded policy in an unparsed/compressed binary is not ruled out.

## Evidence and limitations

- The APP partition contains `/bin/jmcs` (13,406,720 bytes, SHA-256 `cbc7ba881648fb8ffdfcc4c1100a028345c37134a2ae3b9dff7d76572851c232`) and `/bin/linker` (63,176 bytes). This identifies APP as the system filesystem for the captured Honda build.
- jmcs on ext4 is owner 0/group 2000, mode 0755, with no setuid/setgid bit and no extended attributes observed. The init service runs it as root:root.
- UDA `/local/tmp` is mode 0771, owner/group 2000:2000 (`shell:shell`), with no extended attributes. Historical mount evidence says `/data` is read/write without `noexec`; it does not establish SELinux permission.
- Seven ext4 partitions set `EXT4_FEATURE_INCOMPAT_RECOVER`. None was mounted. The read-only `debugfs` queries did not invoke journal recovery.
- The init binary contains `selinux.`, `seclabel`, and `setcon` strings. These show SELinux-related code paths or diagnostics, not that policy was loaded or enforcing. Historical `getenforce` output only says the executable was unavailable.
- A root-to-root exec of a non-setuid, non-file-capability jmcs would normally leave `AT_SECURE` clear absent an LSM secure-exec decision. This is an inference, not a direct auxv measurement; the kernel/LSM state is not established.
- Honda linker `LD_PRELOAD` support remains high-confidence conditional on `AT_SECURE=false` and path access. The current init stanza has no `LD_PRELOAD`; adding service-scoped `setenv` changes the boot ramdisk and is a persistent modification.

Exact GPT geometry, ext4 UUIDs, journal flags, and observed top-level entries are recorded in [the research note](../research/carplay/step41d-selinux-load-environment.md).

## Decision gate

```text
EXT4_READER_SELECTED: e2fsprogs debugfs 1.47.4
WHY_SAFE_READ_ONLY: default read-only debugfs mode (no -w) against disposable partition copies; no mount, journal replay, or repair
COMMANDS_USED: Homebrew e2fsprogs install; read-only Python GPT/superblock and temporary-slice helper; debugfs ls -p/stat/ea_list/cat; streaming SHA-256
PARTITION_MAP: see research/carplay/step41d-selinux-load-environment.md; nine GPT/ext4 entries with UUIDs and recovery flags
SELINUX_PRESENT: PARTIAL (init has SELinux-related strings; no named policy found)
SELINUX POLICY FOUND: NO (no named artifact in inspected filesystems/ramdisks)
FILE_CONTEXTS FOUND: NO
SELINUX_MODE: UNKNOWN
SELINUX ACTIVE: UNKNOWN
JMCS EXEC CONTEXT: UNKNOWN
JMCS PROCESS DOMAIN: UNKNOWN
JMCS CAN MAP /data/local/tmp LIBRARY: UNKNOWN
BEST LIBRARY LOCATION: /data/local/tmp/claritylink_jmcs_interposer.so (candidate only)
LD_PRELOAD HONORED FOR JMCS: UNKNOWN (high-confidence linker support conditional on secure-exec/path access)
AT_SECURE BLOCKER: UNKNOWN (likely false absent an LSM transition; not directly measured)
SERVICE-SCOPED INIT SEAM: NOT READY (requires a boot-ramdisk change and mapping proof)
NO-OP INTERPOSER DESIGN: NOT READY
LIVE NO-OP LOAD TEST: NOT READY
TYPE111 LIVE WORK: NOT READY
BIGGEST BLOCKER: no active policy/context or runtime secure-exec evidence proves a library can be mapped from /data/local/tmp
NEXT ACTION: verify exact init/linker policy-load failure and secure-exec behavior from preserved or pinned Android 4.2.2 sources, then reassess offline readiness
```

## Checks

`git diff --check` passed. This was documentation and read-only filesystem inspection; there were no code tests to run. No vehicle, ADB, raw-image modification, partition mount, session-key access, library deployment, or Type111 action occurred. Temporary partition copies were deleted.
