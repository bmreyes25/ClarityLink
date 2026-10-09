# R7E4 Android 4.2.2 target-path and transfer research

**Scope:** offline planning only. These sources inform the plan; they do not substitute for A0-R observations of the Honda. Evidence classes are intentionally kept separate.

## AOSP_DOCUMENTED

- **Exact source tag:** Android Open Source Project `platform/system/core`, tag `android-4.2.2_r1.2` (tag object `7b05de30ecfed0c224a70c85c7c4c9a58bc81728`). [`rootdir/init.rc`](https://android.googlesource.com/platform/system/core/+/android-4.2.2_r1.2/rootdir/init.rc), blob `0face12110968a14d428c9fef10d3f809a8da280`, creates `/data/local` as `0751 root root` and `/data/local/tmp` as `0771 shell shell` (lines 212–216). It also says the tmp directory should remain empty. The generic fstab-style mount line specifies `/data` with `nosuid,nodev`, without `noexec` (line 136). This is only the base AOSP configuration; vendor init, fstab, kernel, and live mount options may differ. A0-R must inspect `/proc/mounts`; observed `noexec` is a hard blocker, while no `noexec` flag is only `NO_NOEXEC_FLAG_OBSERVED`.
- The same tag's [`toolbox/Android.mk`](https://android.googlesource.com/platform/system/core/+/android-4.2.2_r1.2/toolbox/Android.mk) builds toolbox commands including `ls`, `mount`, `cat`, `ps`, `kill`, `rm`, `getprop`, `chmod`, `id`, and `md5`. SELinux utilities are conditional on `HAVE_SELINUX`; their build presence cannot be assumed.
- [`toolbox/ls.c`](https://android.googlesource.com/platform/system/core/+/android-4.2.2_r1.2/toolbox/ls.c) implements long listing and directory-only options (`-l`, `-d`), supporting the collector's existing `ls -ld` and new `ls -l` calls. The exact Honda result remains authoritative; no fallback is permitted.

## AOSP_DOCUMENTED — SELinux context

Android 4.2.2 does not establish universal SELinux enforcement as a platform baseline; the AOSP toolbox's SELinux tools are build-conditional. Android's [SELinux platform documentation](https://source.android.com/docs/security/features/selinux) describes the later rollout, with SELinux in Android 4.3 and partial enforcement in 4.4. Vendor backports remain possible. Therefore a missing, denied, unreadable, or malformed `/sys/fs/selinux/enforce` result is `SELINUX_STATE_UNAVAILABLE`, informational only. It is not evidence of disabled or permissive state. A separately observed policy denial that blocks the proposed path remains a blocker.

## LEGACY_ADB_IMPLEMENTATION

- **Client source revision:** AOSP `platform/system/core` commit `77d0c65b950570edd5241a8f2ebecfc3acbc5135`, [`adb/file_sync_client.c`](https://android.googlesource.com/platform/system/core/+/77d0c65b950570edd5241a8f2ebecfc3acbc5135/adb/file_sync_client.c). The sync client stats the local file and supplies its mode in `sync_send`.
- The paired legacy file-sync service implementation at the same source revision parses the supplied mode, restricts it to permission bits, creates/opens the destination, and applies `fchmod`. This supports the design expectation that a local 0755 artifact can carry executable bits through ADB sync. It is implementation evidence, not proof of Honda vendor adbd behavior. Remote mode must be verified with `ls -l`; if not executable, stop.
- SHA-256 is the canonical identity. MD5 is an optional transport-consistency comparison only, never cryptographic authenticity.

## HONDA_OFFICIAL_DOCUMENTED

The [2018 Honda Clarity Plug-In Hybrid push-button-start guide](https://owners.honda.com/utility/download?path=%2Fstatic%2Fpdfs%2F2018%2FClarity+Plug-In+Hybrid%2F2018_Clarity_PHEV_Push_Button_Start.pdf) describes ACCESSORY and ON selections without pressing the brake and READY after brake plus POWER. It does not establish ADB reachability or a required test mode. Preserve `SPECIFIC_SAFE_POWER_STATE_SUFFICIENT`, record the operator-observed exact state, and do not require READY or mandate ACCESSORY.

## RELATED_HONDA_PLATFORM

The public [librick/ic1101 ADB notes](https://github.com/librick/ic1101/blob/441db5e2b8cd069c0bfea0ab240c7e1781b4c295/docs/adb.md) (repository `main` snapshot `441db5e2b8cd069c0bfea0ab240c7e1781b4c295`) discuss ADB and USB-role switching on related Mitsubishi Electric Honda/Acura Android 4.2.2 Tegra hardware. This is related-platform evidence only, not Clarity evidence. USB role switching mutates state, so R7E4 does not add it to A0-R. A0-R assumes the intended target is already visible; zero targets means stop.

## CLARITY_STATIC

The checked-in collector performs fixed commands, selects exactly one already-visible `device` target, pins every shell read to its selector, has no retry or fallback, and is disabled by default. R7E4 adds only six literal `ls -l` metadata reads for `/system/bin/toolbox`, `rm`, `ps`, `kill`, `md5`, and `chmod`. These report filesystem-entry observation only and never invoke the inspected binaries.

## CLARITY_HISTORICAL_OBSERVED

Historical ClarityLink repository records and prior offline evidence are not current Honda runtime confirmation. No A0-R, A0-W, Test A, Honda command, target write, USB-role change, or executable transfer occurred in R7E4. Current `/data` mount flags, SELinux state, utility presence, and push-mode behavior still require separately authorized target observation where relevant.
