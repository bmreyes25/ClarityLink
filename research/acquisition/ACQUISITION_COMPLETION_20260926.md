# Reviewed head-unit acquisition completed — September 26 UTC

The resumed head-unit acquisition passes F-B's reviewed scope. It is a live/non-atomic head-unit dataset, not every vehicle ECU, a full Tegra emulator, or proof of boot-independent restoration. No firmware patch or safety/bus modification was made.

## Verification and preservation

- On the head unit, the acquisition log reached storage/metadata completion. All eight selected filesystem archives have final names, no `*.partial` remained, and no acquisition writer was active. Tar warnings were normal leading-slash notices and five ignored live Unix sockets in `/data`.
- The USB-only filesystem was flushed and unmounted before physical removal. On the Mac, all initial 57 recorded hashes passed; all eight tar structures passed, and the reviewed manifest/chunk sizes matched.
- Eight runtime states were captured with user-confirmed UI/audio observations. Required process/display/window/SurfaceFlinger/activity transcripts were nonempty and passed exit/text checks. Casting with center Music mirrored Music; voice worked. The final disconnect restored the Honda interface/compass with casting off.
- Optional `/proc` maps/fd reads were denied in **158** attempts. Their errors are preserved and explicitly recorded unavailable. Legacy ADB transport exit zero does not prove those reads succeeded. One optional firmware-directory metadata result was unavailable. Exposed boot-region candidates were absent in the reviewed manifest; RPMB was inventory-only.
- An interrupted runtime staging directory was preserved inside the new sibling's metadata area. Recognized macOS AppleDouble metadata is retained and hashed. The guarded finalizer retry passed; its initial completion journal contained 2,486 files, then the explicit availability review added one hashed file, bringing the final journal to **2,487**.
- Every final checksum entry passed in each new Mac copy. `SHA256SUMS` and `FINISHED.txt` were independently compared with their USB sources. Originals have no write bits. The old partial original/working copy and September 18 pristine backup were preserved. Old USB configuration, boot, and recovery hash spot checks passed before and after finalization.
- macOS successfully ejected the USB after copying. No additional powered-car work is required for this acquisition.

## Current local copies

Read-only complete original:

`/Users/bmreyes24/ClarityLab/forensic/CLARITY_FORENSIC_20260925_211500_COMPLETE_ORIGINAL`

Current writable analysis copy:

`/Users/bmreyes24/ClarityLab/forensic/CLARITY_FORENSIC_20260925_211500_COMPLETE_WORKING`

The acquisition tree before derived reconstruction totals **9,275,416,154 bytes**. The reconstructed working `mmcblk0-full.img` is **7,549,747,200 bytes**, with SHA-256:

`aa2e2da2a65cb35dbadb2d7bb99b8489faa750db775d6026c222a069b1d72bc6`

Reconstruction verified contiguous chunks, lengths, and hashes. The image matches the earlier independently reconstructed partial-copy image. Both GPT header CRCs, both entry arrays, and nine partition records validate against the mount inventory. Reconstruction/catalog files are derived working-copy outputs, not changes to the original. Raw files, private runtime outputs, manifests, and verification JSON remain local/outside Git.

## Next work and gates

Start a fresh local Codex task using [Prompt 2](../local-model/POST_ACQUISITION_PROMPTS.md) for one simulator fixture. Then prepare Step 3's offline coexistence diagnostic and Step 5's static Identification analysis in separate bounded tasks. Prompt 1 is an optional independent acquisition audit, not a request to repeat copying. The advice-only helper smoke run finished with 6,397 input and 815 output tokens; it does not execute changes or verify correctness.

Codex must verify each deliverable against files/tests, update status, and push a sanitized checkpoint before dependent work advances. Steps 4 and 6 require separately reviewed car diagnostics; receiver installation still depends on Steps 8 and 9. Ordinary runtime dumps neither reveal raw iAP2 Identification packets nor prove active-CarPlay decoder coexistence. Independent iPhone-rendered cluster maps have not been achieved by this acquisition.
