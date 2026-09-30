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

## Step 41D2 preflight — raw ext4 tooling unavailable

The raw GPT partition map was read directly from `../forensic/CLARITY_FORENSIC_WORKING/mmcblk0-full.img`; sector size is 512 bytes. All partition type GUIDs are Microsoft Basic Data (`ebd0a0a2-b9e5-4433-87c0-68b6b72699c7`). Partition roles are left unknown because their directories were not read.

| # | GPT name | Start sector | End sector | Byte offset | Byte length | ext4 UUID | Needs journal recovery |
|---:|---|---:|---:|---:|---:|---|---|
| 1 | CAC | 32,768 | 2,129,919 | 16,777,216 | 1,073,741,824 | `24ba859a-d903-4cb6-ad2c-3cb2a20c1418` | Yes |
| 2 | CAP | 2,129,920 | 3,702,783 | 1,090,519,040 | 805,306,368 | `57f8f4bc-abf4-655f-bf67-946fc0f9f25b` | No |
| 3 | APP | 3,702,784 | 4,751,359 | 1,895,825,408 | 536,870,912 | `57f8f4bc-abf4-655f-bf67-946fc0f9f25b` | No |
| 4 | LOG | 4,751,360 | 5,013,503 | 2,432,696,320 | 134,217,728 | `34f30828-6404-4d06-8257-503d2ef23c7a` | Yes |
| 5 | MITSU | 5,013,504 | 7,110,655 | 2,566,914,048 | 1,073,741,824 | `57f8f4bc-abf4-655f-bf67-946fc0f9f25b` | Yes |
| 6 | SDA | 7,110,656 | 7,372,799 | 3,640,655,872 | 134,217,728 | `ac275c15-c5cb-4ebf-afb0-363130fb52f3` | Yes |
| 7 | SDA2 | 7,372,800 | 7,634,943 | 3,774,873,600 | 134,217,728 | `42c39753-0fa6-4793-b7e5-513bd95f1196` | Yes |
| 8 | SDC | 7,634,944 | 9,732,095 | 3,909,091,328 | 1,073,741,824 | `77fb0698-7c18-4cf6-8dbe-97ee116f42b6` | Yes |
| 9 | UDA | 9,732,096 | 14,712,831 | 4,982,833,152 | 2,550,132,736 | `57f8f4bc-abf4-655f-bf67-946fc0f9f25b` | Yes |

The ext4 reader/tool inventory found no `debugfs`, `e2ls`, `e2cp`, Sleuth Kit (`mmls`, `fls`, `icat`), guestfs, Docker, or Podman executable. `qemu-nbd` is installed and advertises read-only offset exports, but it is not an ext4 filesystem reader and no compatible NBD block-device consumer is installed. Homebrew's expected e2fsprogs bottle path is not present in its cache; no network fetch or installation was performed. The GPT/superblock parser read fixed metadata only and made no mounts or writes.

The `needs_recovery` feature bit is set in seven partitions (all except CAP and APP). Do not use a mount path that could replay journals. A future reader should access the raw image or partition data read-only and must not perform journal replay or filesystem repair. Top-level directory listings, policy/context paths, filesystem roles, and extracted metadata remain unavailable. **Step 41D2 is blocked at tool availability.** Next is Step 41D3: provide a safe offline ext4 inspection environment, then resume with direct read-only inspection.
