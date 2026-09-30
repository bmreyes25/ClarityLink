# Step 41D — Honda SELinux and preload-path evidence audit

**Result: unresolved; no library path is approved by the preserved evidence.** This is an offline audit of the locally held images, archives, and historical capture artifacts. No vehicle, ADB, target write, binary execution, mount, or deployment was used.

## Evidence inventory

The locally held file archives were enumerated by member name: `root-startup.tar`, `system-vendor.tar`, `honda-config.tar`, `media-config.tar`, `userdata-live.tar`, and the forensic `system.tar`/`system-vendor.tar` copies. The complete forensic `system.tar` has 5,543 members; the `system-vendor.tar` copies have 4,347 or 5,543 members depending on acquisition. Exact filename searches found no compiled `sepolicy`, `file_contexts`, `property_contexts`, `service_contexts`, or `seapp_contexts` artifacts in these archives. Matches under `/system/etc/security` were CA certificate files, not SELinux policy.

The saved `boot.img` and `recovery.img` are Android boot images, and the Step 41C CPIO audit found no policy/context files in their ramdisks. The boot ramdisk contains the exact jmcs service source already documented in [jmcs-init-service.md](jmcs-init-service.md). Recovery has no jmcs service. The 2 MiB USP and 64 MiB whole-device MTD artifacts are also present, but this pass did not decode their proprietary filesystems.

The held 7.5 GB `mmcblk0-full.img` has a valid GPT. Its nine partitions are named CAC, CAP, APP, LOG, MITSU, SDA, SDA2, SDC, and UDA. Step 41D2/41D3 installed Homebrew e2fsprogs 1.47.4 and used `debugfs` 1.47.4 against one temporary copy of each partition at a time. The image was never mounted. The copies were deleted after each read. Recursive directory-name walks completed on all nine partitions with no matches for `sepolicy`, `file_contexts` (including common variants), `property_contexts`, `seapp_contexts`, `service_contexts`, `mac_permissions.xml`, `selinux_version`, init rc files, or fstab files. Separate read-only ASCII scans of the USP and whole-device MTD artifacts found no matching SELinux/policy/context terms. These checks establish that named policy/context files were not found in the held filesystems and inspected image artifacts; they cannot exclude a policy embedded in an unparsed/compressed binary or loaded from an unrepresented source.

APP is the system filesystem: its `/bin/jmcs` has size 13,406,720 bytes and streaming SHA-256 `cbc7ba881648fb8ffdfcc4c1100a028345c37134a2ae3b9dff7d76572851c232`, matching the exact archived Honda receiver. It also contains `/bin/linker` (63,176 bytes). CAP has no `/bin/jmcs` or `/bin/linker`. The UDA filesystem is the data filesystem by its root contents; its `/local/tmp` corresponds to `/data/local/tmp`.

## `AT_SECURE` and linker conclusion

**UNKNOWN, with a strong non-secure-exec inference.** The recovered init stanza launches jmcs as `root:root`. The matching binary in APP is mode 0755, owner 0/group 2000, has no setuid/setgid bits, and its ext4 extended-attribute list is empty (no archived file capability or `security.selinux` xattr observed). This removes the ordinary set-ID/file-capability triggers. A root-to-root exec with no effective SELinux transition would normally leave `AT_SECURE` clear, but the exact Honda kernel/LSM decision and runtime auxv are unavailable, so this is not a direct proof.

The archived init binary contains the strings `selinux.`, `seclabel`, and `setcon`. This is **HONDA CONFIRMED** evidence that the init build includes SELinux-related code paths or diagnostics; it does not prove enforcement was enabled at the relevant boot, identify the jmcs security context, or establish whether an LSM secure-exec decision sets `AT_SECURE`. A historical capture records `getenforce: not found`, so it does not supply runtime mode evidence.

The Honda linker’s `LD_PRELOAD` handling remains **HIGH-CONFIDENCE, CONDITIONAL** based on Step 41B's static linker comparison. Its processing for this jmcs invocation is not proven until secure-execution state and actual loader behavior are established.

## Candidate path and mapping permissions

`/data/local/tmp` is the only specific candidate path established by prior init/filesystem evidence. On UDA, `/local/tmp` exists with mode 0771 and owner/group `2000:2000` (`shell:shell`); `/local` is 0751 root:root. `debugfs ea_list` returned no extended attributes for either directory, so no stored `security.selinux` label was observed. Historical mount evidence records `/data` read/write without `noexec`. Root DAC access is plausible, but the exact active SELinux state/domain and executable-mapping permission remain unknown. The init source comments that `/data/local/tmp` should remain empty.

No existing path is therefore proven safe and legitimate for ClarityLink mapping. `/data/local/tmp` remains the best **candidate**, not a confirmed staging path. `/system/lib` exists in APP; `/vendor/lib` was not found in that filesystem. Adding a library to a system/vendor partition would require a persistent partition change. The init stanza currently has no `LD_PRELOAD`; adding a service-scoped `setenv` would itself require changing the boot ramdisk. No zero-change load path has been identified.

## Decision

| Question | Finding | Evidence level |
|---|---|---|
| Matching SELinux policy/context files in the nine ext4 filesystems? | No matches in recursive directory-name walks | Honda image confirmed for names visible in these filesystem trees |
| Matching policy/context files in boot/recovery and inspected MTD images? | No named artifacts found | CPIO inventory and bounded ASCII scans; does not exclude embedded/compressed policy |
| Is SELinux enforcement active for the preserved boot? | Unknown | Init has SELinux-related code strings; no policy file or enforce capture found |
| Is `AT_SECURE` false for jmcs? | Unknown; likely false absent a credential/LSM transition | Exact binary has no set-ID bits/xattrs; process auxv and kernel LSM decision unavailable |
| Does Honda linker support `LD_PRELOAD`? | High confidence, conditional on secure execution and path access | Step 41B static analysis; not live-tested |
| Best candidate path? | `/data/local/tmp/claritylink_jmcs_interposer.so` | Existing `/data/local/tmp` parent is 0771 shell:shell; mapping permissions unknown |
| Exact path with proven read + executable-map access? | None established | SELinux mode/domain and loader execution not confirmed |
| Can current evidence support a no-partition-change load? | No | No existing `LD_PRELOAD` env entry; adding `setenv` requires a boot-ramdisk change |

**Step 41D2/41D3 filesystem inspection: COMPLETE. Step 41D deployment-readiness gate: NOT PASSED.** No named SELinux policy or file-context source was found in any of the nine ext4 filesystems or inspected ramdisks. `AT_SECURE`, process domain, and data-path executable mapping remain unknown; no zero-change load path exists. Do not proceed to a live no-op load test. The remaining useful offline action is to verify the init/linker failed-policy and secure-exec behavior against the exact Android 4.2.2 sources/binaries where available; otherwise preserve these fields as unknown and keep live loading gated.

Once that gate is answered, the proposed sequence remains 41E (offline ARM/API17 package audit), then a separately reviewed Step 42 loader smoke test with Type111 disabled, and only after it preserves stock center CarPlay, Step 43 negotiation-only testing.

## Step 41D2/41D3 read-only filesystem inspection

**Superseded by the completed inspection below.** This was an interim status before installing the user-authorized e2fsprogs reader.

The raw GPT partition map was read directly from `../forensic/CLARITY_FORENSIC_WORKING/mmcblk0-full.img`; sector size is 512 bytes. All partition type GUIDs are Microsoft Basic Data (`ebd0a0a2-b9e5-4433-87c0-68b6b72699c7`). CAP/APP share an ext4 UUID, as do MITSU/UDA; do not rely on UUID-based auto-selection. Root entries were inspected as summarized below; inferred mount roles are kept distinct from the on-disk GPT names.

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

| Partition | Observed top-level entries (directories/files abbreviated only for LOG) | Role assessment |
|---|---|---|
| CAC | `lost+found`, `recovery` | Name retained; role not inferred |
| CAP | `app`, `bin`, `etc`, `framework`, `lib`, `media`, `build.prop` | Android-like filesystem; exact mount role unknown |
| APP | `vendor`, `etc`, `app`, `bin`, `fonts`, `framework`, `lib`, `media`, `usr`, `xbin`, `build.prop`, `recovery-from-boot.p` | System filesystem confirmed by hash-matched `/bin/jmcs` and `/bin/linker` |
| LOG | Diagnostic logs/databases | Log-like contents; private log contents not read |
| MITSU | `ada`, `artwork-1.jpg` | Honda/Mitsubishi data-like contents; exact mount role unknown |
| SDA | `com.honda`, multiple `com.mitsubishielectric.*` directories, `edid.txt` | App/service data-like contents |
| SDA2 | `com.honda`, multiple `com.mitsubishielectric.*` directories, `edid.txt` | App/service data-like contents |
| SDC | `0`, `obb`, `legacy` | Android shared-storage-like contents |
| UDA | `local`, `app`, `app-private`, `app-asec`, `app-lib`, `data`, `system`, `user`, `misc`, `property`, `dalvik-cache`, `tombstones` | Android data filesystem; `/local/tmp` maps to `/data/local/tmp` |

The initial tool inventory found no `debugfs`, `e2ls`, `e2cp`, Sleuth Kit (`mmls`, `fls`, `icat`), guestfs, Docker, or Podman executable. e2fsprogs 1.47.4 was subsequently downloaded and installed from Homebrew at the user's explicit allowance and used. `debugfs` was run without `-w`; one partition copy at a time was held under a temporary directory and deleted after inspection. No filesystem mount, journal replay, repair, raw image rewrite, or live target action occurred.


The `needs_recovery` feature bit is set in seven partitions (all except CAP and APP). No mount was used. A read-only `debugfs` walk listed every partition root and recursively searched names containing SELinux/policy/context tokens plus standard init/fstab names. There were no relevant matches; the only broad `policy` substring matches were ordinary audio policy configuration/library names in APP. APP `/bin/jmcs` streamed to SHA-256 as `cbc7ba881648fb8ffdfcc4c1100a028345c37134a2ae3b9dff7d76572851c232`, exactly matching the known Honda binary. APP `/bin/linker` exists. UDA `/local/tmp` is mode 0771, owner/group `2000:2000`; `/local` is 0751 root:root. `ea_list` returned no extended attributes for jmcs, linker, `/local`, or `/local/tmp`. **Step 41D2/41D3 filesystem inspection is complete; no named policy/context artifact was recovered.** Active mode, jmcs domain, `AT_SECURE`, and mapping permission remain unknown.

### Candidate path observations

| Candidate | Raw ext4 path | Filesystem observation | Can jmcs map it? |
|---|---|---|---|
| `/data/local/tmp/claritylink_jmcs_interposer.so` | UDA `/local/tmp/...` | Parent exists, 0771 shell:shell; no xattr | **Unknown**; policy/domain and executable-map access unproven |
| `/data/local/claritylink/...` | UDA `/local/claritylink/...` | Parent `/local` exists, 0751 root:root; requested child absent | **Unknown**; root could create by DAC, but policy and map access unproven |
| `/data/claritylink/...` | UDA `/claritylink/...` | Requested child absent; UDA root 0771 system:system | **Unknown**; policy and map access unproven |
| `/system/lib/claritylink_jmcs_interposer.so` | APP `/lib/...` | `/lib` exists on system filesystem | **No path proof**; adding a file would require system-partition mutation |
| `/vendor/lib/claritylink_jmcs_interposer.so` | APP `/vendor/lib/...` | `/vendor/lib` absent in APP | **Not established** for this path; no path proof |

The existing `service jmcs` stanza has no `LD_PRELOAD`. Android init/Honda init supports service `setenv` per Step 41C, but adding it would modify the boot ramdisk and require a separate persistent-change review. Thus there is no existing zero-change preload seam even if `/data/local/tmp` later proves mappable.

## Step 41E follow-up (2026-09-30)

Static follow-up in [Step 41E](../../step-reports/41e-init-linker-preload-behavior.md) sharpens but does not close the gate. Honda `/init` has `setenv` parser evidence; the exact jmcs service still has no `LD_PRELOAD`. The preserved linker contains `LD_PRELOAD` and loader machinery strings, but no control-flow proof establishes secure-mode suppression, absolute-path parsing, or missing-library failure behavior. The absence of named policy files plus SELinux-related init strings leaves practical SELinux state **UNKNOWN**, not proven absent/disabled. A root-to-root jmcs exec without set-ID/capability changes makes `AT_SECURE=0` the ordinary expectation, but the actual LSM decision is unknown. `/data/local/tmp` remains an unapproved mapping candidate. The required boot-ramdisk service edit is persistent; no-op load remains **NOT READY**.

### Step 41F linker/mount fingerprint update

Step 41F re-hashed the archived `system-vendor.tar:system/bin/linker` and matched the Step 41B SHA-256. Its ARM ELF contains `LD_PRELOAD`, `LD_LIBRARY_PATH`, generic linker-failure strings, and `/vendor/lib`/`/system/lib` data pointers. Static inspection did not prove the behavior behind those strings. Thus the Honda/AOSP preload match remains **PARTIAL**, exact load/failure behavior UNKNOWN. The historical `/proc/mounts` snapshot at `research/captures/20260925T150706Z-capabilities/capability-survey/cat-_proc_mounts.txt` records `/data` as `rw,nosuid,nodev` without `noexec`; this lowers mount-option concern, but SELinux/mmap permission remains unknown. Mapping risk is assessed MEDIUM. No-op load remains **NOT READY**.
