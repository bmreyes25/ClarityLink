# Historical terminal commands: acquisition recovery

> **Historical only — superseded.** This guide is retained for provenance and contains machine-specific paths and commands. Do not use it for current vehicle work. Follow [NEXT_ACTION.md](../../NEXT_ACTION.md) and the [current read-only network runbook](../runtime/43t0d-live-runbook.md) instead. The old command block is not a portable or currently authorized procedure.

**Historical commands:** this storage resume and subsequent runtime/Mac verification have completed. See [the completion record](ACQUISITION_COMPLETION_20260926.md). Command details below are preserved as historical evidence; do not execute them.

Use these only with the car parked and powered, the same CLARITY USB inserted in the head unit, and Wirebug enabled. The previously shown address was `[REDACTED-PRIVATE-ENDPOINT]:5555`; substitute the current Wirebug address if it changed. The script reads Honda internal storage and writes only the existing new forensic USB sibling. It verifies/skips completed raw images; it never overwrites the original backup. Expect the initial rehash of the completed raw images to take time even when no new file is yet being created.

On the Mac, verify the exact reviewed script and connect:

```sh
cd [REDACTED-LOCAL-REPOSITORY-PATH]
printf '%s\n' 'f358e32107ecefd651bcc5faccc79d2d0e738fec29a16dc525698fb00b98271a  [REDACTED-LOCAL-REPOSITORY-PATH]/research/acquisition/generated/20260925_211500/resume-acquire_headunit.sh' | shasum -a 256 -c -
sh -n [REDACTED-LOCAL-REPOSITORY-PATH]/research/acquisition/generated/20260925_211500/resume-acquire_headunit.sh
adb connect [REDACTED-PRIVATE-ENDPOINT]:5555
adb devices -l
```

The hash check must say `OK`, syntax checking must produce no error, and ADB must list the address as `device`. Stop on a mismatch, `offline`, or `unauthorized`.

Read-only USB preflight:

```sh
adb -s [REDACTED-PRIVATE-ENDPOINT]:5555 shell su -c sh <<'CLARITY_PREFLIGHT'
busybox id
busybox df -h /mnt/usbdrive1
busybox ls -ld /mnt/usbdrive1/CLARITY_BACKUP_20260918_0225 /mnt/usbdrive1/CLARITY_FORENSIC_20260925_211500
exit
CLARITY_PREFLIGHT
```

Both directories must exist; `id` must show the existing root shell. The script independently checks USB identity, mount source, eMMC size, original backup hashes, free space, and the checksum journal. Do not bypass an abort.

Run the resume from the same Mac terminal. Its log gets a new timestamp and shell noclobber prevents overwriting an earlier log:

```sh
CLARITY_RESUME_LOG="[REDACTED-LOCAL-REPOSITORY-PATH]/research/acquisition/live-inventory/20260925T210625Z/resume-$(date -u +%Y%m%dT%H%M%SZ).console.log"
printf 'Saving console log to %s\n' "$CLARITY_RESUME_LOG"
( set -C; adb -s [REDACTED-PRIVATE-ENDPOINT]:5555 shell su -c sh < [REDACTED-LOCAL-REPOSITORY-PATH]/research/acquisition/generated/20260925_211500/resume-acquire_headunit.sh > "$CLARITY_RESUME_LOG" 2>&1 )
tail -n 30 "$CLARITY_RESUME_LOG"
```

In a second Terminal window, this read-only command shows progress; rerun it occasionally:

```sh
adb -s [REDACTED-PRIVATE-ENDPOINT]:5555 shell su -c sh <<'CLARITY_PROGRESS'
busybox tail -n 12 /mnt/usbdrive1/CLARITY_FORENSIC_20260925_211500/acquisition.log
exit
CLARITY_PROGRESS
```

After the first terminal returns, collect the completion state without changing it:

```sh
adb -s [REDACTED-PRIVATE-ENDPOINT]:5555 shell su -c sh <<'CLARITY_CHECK'
busybox cat /mnt/usbdrive1/CLARITY_FORENSIC_20260925_211500/STORAGE_DONE.txt
busybox ls -lh /mnt/usbdrive1/CLARITY_FORENSIC_20260925_211500/filesystems
busybox find /mnt/usbdrive1/CLARITY_FORENSIC_20260925_211500 -name '*.partial'
exit
CLARITY_CHECK
```

Expected archives are `system.tar` (already complete), `system-vendor.tar`, `data-live.tar`, `mitsubishi-live.tar`, `data1-live.tar`, `data2-live.tar`, `media-live.tar`, and `root-startup.tar`. The run closes, tar-lists, hashes, and publishes each archive and then captures metadata. Success requires `STORAGE_DONE.txt`, the archive files, no `.partial`, and no `ABORT` in the saved console. If tar/socket/size/permission errors occur, preserve the partial and error logs and have Codex inspect them; do not delete or manually rename them.

This completes only the storage/archive/metadata substep, not all forensic acquisition. Do not manually create `FINISHED.txt`. Tell Codex when the terminal finishes and keep the car/USB available for review. Once writes have stopped and the script's available flush mechanism has completed, use normal parked shutdown before moving the USB back to the Mac. Codex must then verify `SHA256SUMS` directly on USB, structurally inspect all tar files and error logs, compare the manifest coverage, verify the old backup, document the result, and push the sanitized checkpoint to GitHub. The eight labeled runtime snapshots and final complete Mac original remain later substeps.
# Terminal resume guide

> **Historical only — superseded.** This guide was written for a 2026-09-25 acquisition recovery session and includes machine-specific paths and commands. Do not use it for current vehicle work. Follow [NEXT_ACTION.md](../../NEXT_ACTION.md) and the [current read-only network runbook](../runtime/43t0d-live-runbook.md) instead. The old command block is not a portable or currently authorized procedure.
