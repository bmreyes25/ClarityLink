# September 25 forensic acquisition status

## Current verdict — complete reviewed acquisition

F-B now passes its selected acquisition exit criteria. See [the completion record](ACQUISITION_COMPLETION_20260926.md) for the current original/working paths and exact verification. All eight runtime states were saved and reviewed; the final journal contains 2,487 verified files. Two new Mac copies passed those checks, the original was sealed read-only, and the working eMMC reconstruction/GPT checks passed. The Mac safely ejected the USB. The car can remain off. There are 158 explicitly unavailable optional `/proc` maps/fd attempts; the required Android snapshots succeeded. Native independent CarPlay cluster support is still unproven.

## Resume session update — September 26 UTC

Codex inspected the head unit over existing Wi-Fi ADB after the resume. The script reached `STORAGE_AND_METADATA_DONE` and `STORAGE_DONE.txt` exists. All eight selected filesystem archives have final names; no `*.partial` outputs were found. Their warning files contain only removal of leading slashes and, for the live `/data` archive, five ignored Unix sockets. No acquisition copy/hash process was active when checked. Optional vendor firmware-directory metadata is recorded unavailable. This is storage completion, not final forensic completion.

Before moving the drive to the Mac, `/system/bin/sync` returned successfully, the USB-only `/mnt/usbdrive1` unmount succeeded, and `/proc/mounts` confirmed that mount was absent. On the Mac, all **57** entries in the resumed USB `SHA256SUMS` passed independent hashing. All eight selected tar archives passed structural/header inspection. The manifest matches the reviewed generated manifest and all raw eMMC chunk lengths match it. Spot checks of the old USB backup's configuration, boot, and recovery files passed before and after finalization; none of its files was written. Every file/directory in the pristine September 18 Mac backup has zero write permission bits. Eight labeled runtime snapshots were collected to the Mac separately, then copied and verified into the new forensic sibling. Interrupted staging and macOS FAT32 metadata were preserved and reviewed; the [finalizer regression record](FINALIZER_VERIFICATION_20260926.md) explains the guarded resume. Local-model tasks are in [the post-acquisition prompt sheet](../local-model/POST_ACQUISITION_PROMPTS.md).

## Earlier verified partial baseline

Before the resume, the initial USB dataset had 25 verified checksum entries: eight numbered eMMC chunks totaling 7,549,747,200 bytes; eight named MTD images; a 736,225,280-byte `/system` tar; the manifest; and seven initial metadata outputs. This describes the historical partial copy, not the current resumed USB contents.

The first acquisition stopped during the initial filesystem archive because its FAT32 comparison used an Android 32-bit shell integer test. The patched template uses BusyBox `awk`. The reviewed generated resume script has now run successfully; its earlier syntax check and the resumed acquisition log are preserved locally.

All previously missing selected archives and storage metadata were acquired and verified on USB. Historical `.original` journals and `.sha256` sidecars were preserved. F-B's runtime, finalization, and complete-copy requirements have subsequently passed; do not repeat the storage acquisition.

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

Next offline work: catalog firmware in the new complete working copy, strengthen the simulator, prepare the reviewed decoder diagnostic, and trace receiver Identification using sanitized derived evidence. Do not replace the historical partial original or the September 18 pristine backup. Native independent CarPlay cluster support and boot-independent recovery remain unproven.
