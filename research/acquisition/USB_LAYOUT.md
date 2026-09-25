# Proposed USB and Mac layout

```text
/mnt/usbdrive1/
├── CLARITY_BACKUP_20260918_0225/       # existing; never write, rename, or delete
├── Wirebug.apk                          # if already present; leave alone
└── CLARITY_FORENSIC_YYYYMMDD_HHMMSS/   # new, unique sibling only
    ├── README.txt
    ├── device-map.txt
    ├── acquisition.log
    ├── SHA256SUMS
    ├── ACQUISITION_MANIFEST.json         # exact reviewed manifest, embedded by script
    ├── emmc/
    │   ├── mmcblk0.part000
    │   └── ...
    ├── boot-regions/                     # boot0/boot1 only if already readable
    ├── mtd/                              # documented mtdblock0–7 only
    ├── filesystems/                      # selected live tar archives and error logs
    ├── metadata/                         # bounded proc/sys/HAL/package inventory
    ├── runtime/                          # state-labeled snapshots
    └── FINISHED.txt                      # written only after all selected steps verify
```

All in-progress output uses `.partial` inside the new forensic directory and receives its final name only after the copy closes, its expected length is checked, and SHA-256 is recorded. The exact generated manifest is embedded in the reviewed script and saved inside the sibling; the Mac finalizer compares that copy byte-for-byte with the reviewed manifest before marking completion. Completed chunks are never overwritten; a resume verifies and skips them or aborts on mismatch. A torn checksum-journal line causes an abort for manual offline review. The backup directory is checked for existence and known hashes before the first new output. No acquisition output may resolve outside the new sibling directory under `/mnt/usbdrive1`.

After a reviewed acquisition: verify hashes **on the USB** from the Mac, copy the forensic directory to `/Users/bmreyes24/ClarityLab/forensic/CLARITY_FORENSIC_ORIGINAL`, verify again, and make that original copy read-only. Create a separate `/Users/bmreyes24/ClarityLab/forensic/CLARITY_FORENSIC_WORKING` for extraction/emulation. Reconstruct `mmcblk0-full.img` only from verified chunks in the working copy and hash it separately. These Mac paths are future outputs; do not create them before the acquisition is approved. Both forensic directories and all raw captures stay outside Git.
