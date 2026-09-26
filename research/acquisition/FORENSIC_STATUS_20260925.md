# September 25 forensic acquisition status

The new USB sibling `CLARITY_FORENSIC_20260925_211500` is a **verified partial acquisition**, not a finished forensic set. On the mounted CLARITY USB, all 25 paths in its `SHA256SUMS` matched SHA-256: eight numbered eMMC chunks totaling 7,549,747,200 bytes; eight named MTD images; a 736,225,280-byte `/system` tar; the manifest; and seven initial metadata outputs. The Mac working copy matched the same manifest. The independent September 18 pristine backup directory remains mode `0500`; spot checks of `honda-config.tar`, `boot.img`, and `recovery.img` passed. No source block device or original backup was modified.

The acquisition stopped during the first filesystem archive because the original script compared its byte size to a FAT32 limit using an Android 32-bit shell integer test. The system tar was later structurally checked, hashed, and published, but the remaining archive/metadata phase did not run. The patched template uses BusyBox `awk` for that comparison. A generated resume script exists locally and has passed `sh -n`; it has **not** been run on the car.

Missing selected archives: `system-vendor.tar`, `data-live.tar`, `mitsubishi-live.tar`, `data1-live.tar`, `data2-live.tar`, `media-live.tar`, and `root-startup.tar`. Most planned kernel/HAL/sysfs metadata, eight labeled runtime snapshots, `STORAGE_DONE.txt`, and final `FINISHED.txt` are absent. Extra `.original` journals and `.sha256` sidecars on the USB were preserved as found. Do not run the strict finalizer or mark the acquisition complete until these are reviewed and the missing steps are performed or the acquisition scope is explicitly changed.

The verified Mac copy is at `/Users/bmreyes24/ClarityLab/forensic/CLARITY_FORENSIC_20260925_211500_PARTIAL_ORIGINAL` and is read-only. The writable analysis copy is `/Users/bmreyes24/ClarityLab/forensic/CLARITY_FORENSIC_WORKING`. Its reconstructed `mmcblk0-full.img` is 7,549,747,200 bytes with SHA-256 `aa2e2da2a65cb35dbadb2d7bb99b8489faa750db775d6026c222a069b1d72bc6`; reconstruction used only individually verified chunks. The original backup is separate from both.

The primary GPT header, entry array, and backup GPT header CRCs match. All nine partition starts show an ext4 superblock signature. The live mount inventory supplies these mappings; writable partitions in this image were read live and may not be filesystem-consistent at a single instant.

| GPT partition | Start LBA | Size (MiB) | Live mount | Live state |
|---|---:|---:|---|---|
| CAC | 32768 | 1024 | `/cache` | rw |
| CAP | 2129920 | 768 | `/system/vendor` | ro |
| APP | 3702784 | 512 | `/system` | ro |
| LOG | 4751360 | 128 | `/log` | rw |
| MITSU | 5013504 | 1024 | `/data/MitsubishiElectric` | rw |
| SDA | 7110656 | 128 | `/mnt/data1` | rw |
| SDA2 | 7372800 | 128 | `/mnt/data2` | rw |
| SDC | 7634944 | 1024 | `/mnt/media` | rw |
| UDA | 9732096 | 2432 | `/data` | rw |

Next offline work: parse and catalog the verified working image without writing it; compare firmware files with the September 18 backup; continue the simulator and protocol analysis using sanitized derived evidence. Next car work, only in a reviewed parked session: inspect the exact resume script and run card, finish missing USB archives/metadata, collect labeled runtime states, verify all hashes directly on USB, then create a separate **complete** original Mac copy. Do not replace the partial original or the September 18 pristine backup.
