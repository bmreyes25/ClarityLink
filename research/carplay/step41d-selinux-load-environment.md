# Step 41D — Honda SELinux and preload-path evidence audit

**Result: unresolved; no library path is approved by the preserved evidence.** This is an offline audit of the locally held images, archives, and historical capture artifacts. No vehicle, ADB, target write, binary execution, mount, or deployment was used.

## Evidence inventory

The locally held file archives were enumerated by member name: `root-startup.tar`, `system-vendor.tar`, `honda-config.tar`, `media-config.tar`, `userdata-live.tar`, and the forensic `system.tar`/`system-vendor.tar` copies. The complete forensic `system.tar` has 5,543 members; the `system-vendor.tar` copies have 4,347 or 5,543 members depending on acquisition. Exact filename searches found no compiled `sepolicy`, `file_contexts`, `property_contexts`, `service_contexts`, or `seapp_contexts` artifacts in these archives. Matches under `/system/etc/security` were CA certificate files, not SELinux policy.

The saved `boot.img` and `recovery.img` are Android boot images, and the Step 41C CPIO audit found no policy/context files in their ramdisks. The boot ramdisk contains the exact jmcs service source already documented in [jmcs-init-service.md](jmcs-init-service.md). Recovery has no jmcs service. The 2 MiB USP and 64 MiB whole-device MTD artifacts are also present, but this pass did not decode their proprietary filesystems.

The held 7.5 GB `mmcblk0-full.img` has a valid GPT. Its nine partitions are named CAC, CAP, APP, LOG, MITSU, SDA, SDA2, SDC, and UDA. Read-only superblock inspection found ext4 magic `0xEF53` at the expected superblock offset in all nine partitions. Existing filesystem exports cover `system.tar` and the other named filesystem snapshots, but the raw MMC ext4 directories were not independently decoded during this audit; no ext4 reader is available in the current offline toolset. Therefore this pass establishes absence from the enumerated archives and ramdisks, **not** absence from every byte of the raw MMC image. The raw image is the remaining already-held source that might contain an unexported policy artifact; no partition-to-path mapping for policy was recovered.

## `AT_SECURE` and linker conclusion

**UNKNOWN.** The recovered init stanza launches `/system/bin/jmcs` as `root:root`, and the archived jmcs file is mode 0755 with no setuid/setgid mode bits. Those facts make a real/effective UID or GID mismatch less likely, but they do not prove `AT_SECURE=0`: the archived file exports omit filesystem xattrs/file capabilities, and the exact Honda SELinux policy and exec transition are unavailable.

The archived init binary contains the strings `selinux.`, `seclabel`, and `setcon`. This is **HONDA CONFIRMED** evidence that the init build includes SELinux-related code paths or diagnostics; it does not prove enforcement was enabled at the relevant boot, identify the jmcs security context, or establish whether an LSM secure-exec decision sets `AT_SECURE`.

A historical capture records `getenforce: not found`. This is not evidence that SELinux was disabled; it only shows that this diagnostic executable was unavailable. No captured `/sys/fs/selinux/enforce`, process security context, auxv `AT_SECURE`, or AVC record was found in the reviewed files.

The Honda linker’s `LD_PRELOAD` handling remains **HIGH-CONFIDENCE, CONDITIONAL** based on Step 41B's static linker comparison. Its processing for this jmcs invocation is not proven until secure-execution state and actual loader behavior are established.

## Candidate path and mapping permissions

`/data/local/tmp` is the only specific candidate path established by prior init/filesystem evidence: init creates it with mode 0771 and owner/group `shell:shell`; historical mount evidence records `/data` read/write without `noexec`. A root process can pass the ordinary DAC read check for a shell-owned file, but the evidence does not establish the path's SELinux label, jmcs domain access, executable-mapping permission, or whether Honda's linker would accept a preload from it. The init source also comments that this directory should remain empty.

No existing path is therefore proven safe and legitimate for ClarityLink mapping. `/data/local/tmp` remains a **candidate requiring policy proof**, not a recommendation to stage a library there. `/system/lib` would avoid a data mount but cannot be used without a persistent system-partition change and is outside the desired no-partition-change route.

## Decision

| Question | Finding | Evidence level |
|---|---|---|
| Matching SELinux policy/context artifacts in enumerated archives or boot/recovery ramdisks? | No | Archive/CPIO inventory; Honda confirmed for those inspected artifacts |
| Matching policy present somewhere in the raw MMC image? | Unknown; raw GPT image exists but its relevant partition contents were not decoded here | Unknown |
| Is SELinux enforcement active for the preserved boot? | Unknown | Historical `getenforce` command unavailable; no enforce file/context capture |
| Is `AT_SECURE` false for jmcs? | Unknown | Root:root service and non-setuid mode do not settle LSM/file-capability behavior |
| Does Honda linker support `LD_PRELOAD`? | High confidence, conditional on secure execution and path access | Step 41B static analysis; not live-tested |
| Exact pre-existing path with proven read + executable map access? | None established | Unknown |
| Can current evidence support a no-partition-change load? | No | Path and SELinux permissions unproven |

**Step 41D gate: NOT PASSED.** Do not proceed to Step 42. The next offline action is to use a read-only ext4 reader to enumerate the nine preserved filesystems, identify any policy/context files and their metadata, then correlate the relevant policy to the active boot/init image. Preserve the image; do not modify partitions. If no such policy/context source exists in the held image, the `AT_SECURE` and path-permission questions stay unresolved and a live loader test is not justified.

Once that gate is answered, the proposed sequence remains 41E (offline ARM/API17 package audit), then a separately reviewed Step 42 loader smoke test with Type111 disabled, and only after it preserves stock center CarPlay, Step 43 negotiation-only testing.
