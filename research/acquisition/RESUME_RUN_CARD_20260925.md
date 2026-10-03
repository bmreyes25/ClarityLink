# Parked-car resume card for the partial September 25 acquisition

**Historical execution card:** this resume has now run and the reviewed acquisition passed [final verification](ACQUISITION_COMPLETION_20260926.md). Do not rerun it against the finalized USB sibling. The notes below preserve the pre-run state and exact reviewed procedure.

**Current state:** USB is on the Mac; no ADB device is connected. This card is preparation only. The eight raw eMMC chunks, eight MTD images, and `/system` tar already verified on USB. The next run must resume the same forensic sibling; it must not start a new raw copy or change the September 18 backup.

Reviewed local inputs (ignored from Git because the embedded manifest contains device identity):

- `research/acquisition/generated/20260925_211500/resume-acquire_headunit.sh` — SHA-256 `f358e32107ecefd651bcc5faccc79d2d0e738fec29a16dc525698fb00b98271a`
- `research/acquisition/generated/20260925_211500/ACQUISITION_MANIFEST.json` — SHA-256 `062f663e68693eae6d110c4ded0816da1d25888f73264c30153d26befa1da0ce`
- Only destination: `/mnt/usbdrive1/CLARITY_FORENSIC_20260925_211500`.

The script checks the FAT32 mount source, USB identity/size, eMMC size, old backup hashes, destination marker, and prior checksum journal. It rehashes and skips completed eMMC/MTD files, then archives the remaining approved filesystem paths and captures bounded metadata. Every `dd` input is a documented storage node; every output resolves under the new USB sibling. No `of=/dev/block`, remount, flash, `force_ro`, MTD erase, bus access, or vehicle control is present. The shell syntax passes `sh -n`, and the patched FAT32 byte-size comparisons use BusyBox `awk` to avoid the Android shell's 32-bit integer overflow. A failed archive leaves a `.partial` for manual review and must not be blindly retried.

When the car is parked and powered, insert the same USB and enable Wi-Fi ADB. On the Mac, check the script hashes above and run `adb devices -l`; use the currently displayed Wirebug address if it changed. Confirm `/mnt/usbdrive1` is the FAT32 mount and the forensic sibling and old backup are present. Then execute the exact script over the existing root shell, saving console output **only on the Mac**:

```sh
cd /Users/bmreyes24/ClarityLab/clarity-analysis
shasum -a 256 research/acquisition/generated/20260925_211500/resume-acquire_headunit.sh
sh -n research/acquisition/generated/20260925_211500/resume-acquire_headunit.sh
adb -s [REDACTED-PRIVATE-ENDPOINT]:5555 shell su -c sh < research/acquisition/generated/20260925_211500/resume-acquire_headunit.sh > research/acquisition/live-inventory/20260925T210625Z/resume.console.log 2>&1
```

Use the current serial in place of `[REDACTED-PRIVATE-ENDPOINT]:5555` if Wirebug changed it. Do not treat ADB's exit code alone as success: verify the console and USB `acquisition.log`, presence of `STORAGE_DONE.txt`, absence of `.partial`, and SHA-256 for every listed file. Keep the car powered until the script closes and the USB filesystem flushes. If it aborts, stop and inspect the named partial/error file; do not delete or overwrite a completed chunk.

The eight labeled runtime states remain a separate bounded capture using `runtime_snapshot.py` and normal parked UI actions. They should be captured only after the storage resume is complete, then the Mac finalizer can verify and create `FINISHED.txt`. Copy that **complete** USB sibling to a new complete Mac original and verify again; never replace `CLARITY_FORENSIC_20260925_211500_PARTIAL_ORIGINAL` or the September 18 pristine backup. The raw eMMC image is live/non-atomic and does not satisfy the boot-independent recovery gate.
