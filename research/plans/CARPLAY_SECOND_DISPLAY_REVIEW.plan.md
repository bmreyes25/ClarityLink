# Clarity CarPlay second display — reviewable execution plan

**Status:** execution started with a local Git baseline; forensic acquisition added for separate review, 2026-09-25. No bulk copy has started. Analysis/design work stays under `/Users/bmreyes24/ClarityLab/clarity-analysis`. The later forensic Mac copies have their own paths below. `/Users/bmreyes24/ClarityLab/backups/CLARITY_BACKUP_20260918_0225_ORIGINAL` remains untouched, read-only, and outside Git. Every future on-car install or change needs its own exact artifact, run card, rollback, and approval.

## Target and present verdict

**Success** means an active iPhone Apple Maps route produces an *independent, iPhone-rendered* map or maneuver view in the Clarity's physical Navigation rectangle while the center CarPlay screen shows Music; voice guidance still plays, ending the route or unplugging the iPhone clears the cluster, and speed/warnings remain visible. Prove provenance by recording a distinct iPhone cluster display setup/stream identity, tying decoded cluster frames to that channel, and observing route/map updates while Music stays foreground. A synthetic image or center-screen mirror cannot pass. Test Waze separately. A Honda-drawn arrow/distance is a useful fallback but does not count as a second CarPlay display. CarPlay Ultra and spatial audio are outside this plan.

We do **not** yet know whether this receiver can negotiate the required second stream. Static inspection finds one `gMainScreen` registration in `jmcs`, display information built from the main screen, and a singleton `libcarplay_proxy.so` screen callback. The existing Honda Hack cast is a center-screen mirror: it changed from Maps to Music with the center screen. Head-unit Waze proved the cluster can instead show independent arrow/distance, but that path has not received iPhone route metadata and its ordinary layout omits road names. A prior temporary test observed 28/30 output frames on each of two NVIDIA decoders; it did not test coexistence with active CarPlay. The kernel's `CONFIG_USB_MON` is unset, and ordinary ADB/logcat did not expose raw iAP2 Identification bytes. The USB-C-to-A Mac cable did not enumerate a wired ADB device; Wi-Fi ADB worked.

Evidence: [receiver audit](../native/receiver-multidisplay-audit.md), [implementation gates](NATIVE_CLUSTER_IMPLEMENTATION_GATES.md), [session findings](../captures/20260925T150706Z-SESSION_FINDINGS.md), [Waze positive control](../captures/20260925-WAZE_HEADUNIT_FINDINGS.md). Apple's [WWDC19 CarPlay systems session](https://developer.apple.com/videos/play/wwdc2019/252/) describes distinct cluster video streams and a separate iAP2 Route Guidance metadata path; [WWDC23](https://developer.apple.com/videos/play/wwdc2023/10150/) again distinguishes phone-rendered cluster UI from vehicle-rendered guidance. Those are protocol possibilities, not proof of Honda implementation.

## What we still need to establish

| Unknown | Decisive evidence | Why it matters |
|---|---|---|
| Exact current Identification and CarPlay display capabilities | Validated raw exchange or a separately labeled static reconstruction, with bytes/field provenance | Shows what the iPhone is actually told; generic strings and log lines are insufficient. |
| Whether this receiver can speak the newer multi-display session protocol | A traced capability/setup path and, ultimately, a successful second display setup on a non-car harness or approved car test | A second-screen XML flag cannot supply missing protocol and stream dispatch. |
| Whether iPhone sends usable maneuver metadata | Decoded iAP2 Route Guidance events during a known route, or an explicit unknown if capture is incomplete | Determines whether the Honda-rendered fallback can use real iPhone data. |
| Center CarPlay + extra decoder coexistence | Bounded additional decode while factory CarPlay remains visible and voice works, with output timing/memory and complete cleanup | Two diagnostic decoders with CarPlay disconnected do not establish this. |
| Precise safe rendering geometry and ownership | Photo-to-HDMI calibration plus display-1 layer/surface behavior | Keeps custom content inside the Navigation area. |
| Recovery after failed receiver start | Boot-independent, tested restoration of exact original files and startup state | A verified backup alone does not prove an unbrick path. |

## Dependency map

```text
1 Git/evidence → F-A Offline acquisition design → F-B Reviewed parked acquisition
                                                    ↓
                         2 Twin/viewport → 3 Decoder probe → 4 CarPlay coexistence
                                                    ↓
                                           5 Static Identification
                             ├─ sufficient evidence ──────┐
                             └─ ambiguity → 6 Capture ────┤
                                                            ↓
                                                    7 ABI/receiver design
                                                     ↙              ↘
                                               8 Recovery       9 Candidate
                                                     ↘              ↙
                                                  10 Renderer test
                                                          ↓
                                                  11 Receiver test
                                                          ↓
                                             12 Apple Maps, then Waze
```

**Execution order:** 1 → F-A → F-B → 2 → 3 → 4 → 5 → 6 (only if static work leaves a material question) → 7 → 8/9 → 10 → 11 → 12. The forensic phase is a *head-unit* acquisition, not a dump of unrelated vehicle ECUs. No script may start the large copy until the fresh read-only inventory, exact space calculation, generated commands, and run card are reviewed. Step 5 may proceed offline while the decoder probe is prepared, but the short coexistence car test comes before an expensive packet-capture car session. Steps 1–3, 5, 7, and 9 are Mac-only. Steps 4 and 6 require separately reviewed parked-car run cards. Step 8 remains a recovery evidence gate; a full disk image is not a proven restoration path. Steps 10–11 each require review of the exact vehicle-changing artifact.

## 1. Create a Git and evidence baseline (Mac only)

**Context for a fresh executor:** work in `/Users/bmreyes24/ClarityLab/clarity-analysis`. Read the four evidence documents linked above and `research/simulator/INFOTAINMENT_TWIN_SCOPE.md`. Do not write to the original backup. The local Git baseline is complete; `research/` also contains large downloaded tools and extracted firmware, so never run `git add .` without an audited ignore list.

**Tasks:** initialize a Git repository with a reviewed `.gitignore`. Track research notes/plans, simulator source, parsers/probe source and fixtures, build scripts, contracts, manifests, and candidate source. Exclude original/working firmware archives and images, `extracted/`, downloaded JDK/tools, bulk decompiler output, build products, raw packet captures, route/phone identifiers, and other sensitive or large data. Audit the tracked-file list and size before publishing to the user-requested private GitHub repository. Inventory receiver binaries/config, prior captures, original backup hashes, probe APK uninstall evidence, simulator tests, and Honda Hack settings. Build `research/evidence/second-display-ledger.md` with columns `claim / raw artifact / observation or inference / confidence / missing proof`. Record one-screen call sites and singleton proxy offsets; measure navigation-region bounds from photos with uncertainty.

**Exit/verification:** `git status --short` and `git ls-files` show only intended code/docs, no backup, private capture, credentials, or bundled tool; ledger links resolve, hashes match, and existing simulator tests pass. **Rollback:** remove only the local Git metadata and derived files if needed; original artifacts remain unchanged.

## F-A. Design the forensic head-unit acquisition (Mac only; underway)

**Context:** the existing verified backup has filesystems and selected images but no full raw eMMC user-area image. Historical `/proc/partitions` reports a 7,549,747,200-byte `/dev/block/mmcblk0`; current size, eMMC boot regions, readable MTD list, applets, and USB free space must be reconfirmed. The same FAT32/MBR USB may be used, with a **new unique sibling** `CLARITY_FORENSIC_YYYYMMDD_HHMMSS` next to the immutable `CLARITY_BACKUP_20260918_0225`. Do not reformat or modify the old backup directory.

**Work:** use [the read-only inventory commands](../acquisition/READ_ONLY_INVENTORY.md) to record `/proc/partitions`, `/proc/mtd`, `fdisk`, block/by-name links, mounts, USB identity and `df`, filesystem size estimates, source readability, and BusyBox applets. Update the [storage map](../acquisition/STORAGE_MAP.md) *before* generating the exact copy script. The [space budget](../acquisition/SPACE_BUDGET.md) currently gives only a provisional 20 GiB free-space floor; the live inventory must calculate the current requirement plus safety margin. Review the [USB layout](../acquisition/USB_LAYOUT.md), [script source/template](../acquisition/acquire_headunit.sh.in), generated per-device chunk manifest, and [parked run card](../acquisition/ON_CAR_FORENSIC_ACQUISITION_RUN_CARD.md). Use ~1 GiB FAT32-safe chunks with expected sizes from the *fresh* device size. Include raw eMMC, already-readable boot0/boot1 if present, documented readable MTD storage, filesystem archives, selected `/proc` and safe sysfs/HAL metadata, and bounded runtime snapshots. RPMB is inventory-only. No partition write, `force_ro` change, remount, MTD erase, bus access, or security weakening.

**Exit/verification:** source paths appear only as `if=`/read inputs; every output is guarded beneath the new USB sibling. The exact generated script refuses mismatched live sector size, absent backup, hash mismatch, low free space, or an existing completed chunk with a wrong hash. A fresh script and run card are presented for review; **do not start the acquisition at this gate**. All raw and private outputs stay outside Git.

## F-B. Acquire in a reviewed parked session, then verify on the Mac (not yet authorized)

**Context:** run only after F-A's exact storage map, applet list, selected devices, calculated free space, generated script/hash, and run card are reviewed. The Honda devices are read-only *sources*; all car-side writes go to new files inside the unique USB forensic sibling. Full raw eMMC is a live, non-atomic image; do not unmount writable Android filesystems to improve consistency. The run may take longer than a short diagnostic; use chunk checkpoints and agreed time/power conditions, not a guessed duration.

**Work:** verify existence and several known hashes from the old USB backup without changing it. Capture `/dev/block/mmcblk0` in numbered ~1 GiB chunks, accessible boot0/boot1, and documented storage MTD blocks. Save SHA-256 for each completed output, logs, and tar verification/error output. Archive `/system`, `/data`, `/mnt/data1`, `/mnt/data2`, `/mnt/media`, root/startup and Honda config as supported, reusing the earlier backup's lessons. Capture bounded runtime states: disconnected, CarPlay Home, Maps open, active route, route with center Music, factory cluster Navigation, Honda Hack casting, then disconnected. Attempt read-only `/proc/<pid>` cmdline/status/maps/fd for receiver, CarPlay, display, Navigation, SurfaceFlinger, and media processes; record permission denial rather than bypassing it. Capture hardware/kernel metadata and inventory HAL, EGL/GLES, Tegra, USB, audio, display, and named CarPlay/cluster components. Hash and verify all selected outputs; write `FINISHED.txt` only after complete verification. Stop and preserve `.partial` files if a copy fails; never silently overwrite a completed chunk.

**Mac verification:** verify USB `SHA256SUMS`, copy the forensic directory to `/Users/bmreyes24/ClarityLab/forensic/CLARITY_FORENSIC_ORIGINAL`, verify again and make it read-only, then create a separate `CLARITY_FORENSIC_WORKING` copy. Reconstruct and hash `mmcblk0-full.img` from verified chunks in the working copy, parse the partition table, and compare to live inventory and the old backup. Raw `/data` and disk images can contain Wi-Fi, phone, route, account, or session data: keep them local/outside Git and never upload them. The acquisition is head-unit-only; any independent cluster MCU investigation would need a separate read-only plan.

**Exit/verification:** every selected image/archive has length and SHA-256 evidence, storage map reconciles, runtime states are labeled, and Mac original/working copies are distinct. The existing boot-independent recovery gate remains unchanged. **Rollback:** stop reads, leave old backup untouched, retain incomplete new sibling for review; do not delete data to make space.

## 2. Make the infotainment twin a reliable oracle (Mac only)

**Context:** the existing browser twin at `research/simulator/` replays Honda casting and head-unit Waze, plus a hypothetical second-stream contract. It is an infotainment test harness, not an ECU or full cluster-electronics emulator.

**Tasks:** integrate the forensic dataset in four bounded layers: (1) partition/filesystem and firmware catalog for Ghidra/JADX/native work; (2) Android/application twin with mocked Binder, Honda Navigation/ExternalDisplay, and display/audio services; (3) native receiver ABI harness with mocked USB/MFi/display/audio and replayed runtime fixtures; (4) dual-display infotainment twin modeling 800×480 center, HDMI/display-1, calibrated physical Navigation rectangle, main/cluster lifecycle, Maps→Music, route end, disconnect, and stale cleanup. Add photo-calibrated bounds and explicit center/cluster provenance. Ingest saved paired screenshots and Waze events as observed fixtures; keep hypothetical iPhone stream and route metadata visibly synthetic. Assert that a mirror follows Music and an independent stream does not. Investigate a full Android/QEMU boot only after these layers are useful; complete Tegra hardware emulation is not a prerequisite.

**Exit/verification:** repeatable tests and a browser replay comparing three labeled modes: observed mirror, observed Honda guidance, proposed second stream. No production vehicle bus interface. **Rollback:** revert only simulator working files from the Step 1 manifest.

## 3. Prepare a CarPlay-coexistence decoder probe (Mac only)

**Context:** the earlier no-permission API-17 diagnostic APK was installed and removed after approval. It measured two simultaneous 800×480 NVIDIA decoders with CarPlay disconnected, each producing 28/30 frames. The two missing frames and real center-CarPlay coexistence remain unresolved.

**Tasks:** inspect the original output/EOS timing and fix the measurement criterion offline rather than relabeling 28/30 as full success. Under `research/probes/carplay-coexistence/`, make a background-safe bounded variant that leaves the center CarPlay UI in front and runs **one** extra 800×480 H.264 stream at 15 fps for 60 seconds. Record actual output frame timestamps, codec identity, dimensions, dropped/error frames, available memory/thermal readings, and an explicit `unavailable` for unsupported sensors. Predeclare the candidate gate: at least 95% of submitted frames output after decoder drain, no output gap over 250 ms after startup, no codec error, and no observed center CarPlay freeze or voice interruption. This is a diagnostic engineering threshold, not an Apple requirement or proof of two CarPlay streams. No network, root, audio, vehicle, overlay, or bus permissions. Prepare signed APK/hash, exact install/start/stop/uninstall commands, timeout, and post-uninstall checks. Bench-test the state machine and manifest; preserve a copy of the prior APK and its result.

**Exit/verification:** reviewable source/APK/run card and meaningful offline tests. Merely obtaining a codec instance is not a pass. **Rollback:** no car write in this step.

## 4. Measure coexistence (one short parked session, only after Step 3 review)

**Context:** this step temporarily writes only the approved diagnostic app package/data, then removes it. It is separate from protocol capture so a failed test does not compromise both experiments. CarPlay and Apple Maps voice start in a known working state.

**Tasks:** record baseline center/cluster/voice; run the predeclared 800×480/15 fps/60-second decode behind active CarPlay; collect actual frame timing, one-per-second center-display observations, and spoken-guidance observations before/during/after the run. Record available memory/thermal readings and their absence when unsupported. Stop immediately on CarPlay failure, warning, unusual lag, or unexpected app behavior. Force-stop and uninstall the exact package, verify package/data removal, and recheck center CarPlay, voice, and normal cluster. Do not exercise vehicle controls or bus APIs.

**Exit/verification:** a measured pass/fail/unknown against the Step 3 threshold for the tested resolution, frame rate, duration, and CarPlay coexistence, with restoration evidence in `research/captures/`. Human audio observation is reported separately from timestamped frame data. This still does not prove that iPhone will negotiate a second stream. **Rollback:** exact run card uninstall and normal-session restoration; stop if cleanup cannot be verified.

## 5. Reconstruct Identification statically, then design capture if needed (Mac only)

**Context:** ordinary logcat, display screenshots, wired ADB, and the current head-unit kernel cannot reveal the missing raw iAP2 Identification payload. Start with copied `jmcs` and configuration before considering an inline analyzer. A USB stick can carry a diagnostic APK or receive log files; it cannot observe traffic passing between iPhone and head unit by itself. Linux [usbmon documentation](https://docs.kernel.org/usb/usbmon.html) also warns that transfer length need not mean payload bytes are present in a text capture.

**Tasks:** trace Honda configuration and screen initialization into the iAP2 Identification serializer and CarPlay display/session setup in copied `jmcs`/libraries. For every field, record source function/virtual address, derivation, encoding, and confidence in `research/protocol/static-identification.md`. Create a Mac fixture that serializes the reconstructed *current* one-screen model; label predicted bytes as static, never observed. Record what static analysis does and does not settle. Only for material uncertainty, write `research/protocol/capture-design.md` with a decision tree: (A) candidate inline USB analyzer, never assumed transparent, whose USB role/topology, speed, power, connectors, full-payload recording, pass-through/authentication behavior, and export format are validated on a Mac bench and checked against Honda's actual connection before capture; (B) a future narrowly scoped receiver-side trace only if its exact code changes and boot-independent recovery are reviewed; (C) if neither is feasible, static-only verdict marked `unknown`. Do not purchase hardware until a model meets these criteria. Build an offline parser/validator under `research/protocol/` only if capture is selected; preserve framing/checksums, undecoded fields, timestamps, and hashes. Keep phone identifiers and route/location data local.

**Exit/verification:** `research/protocol/static-identification.md` has reproducible binary cross-references, a tested serialization fixture, and an explicit `known/unknown` table. If capture remains necessary, `capture-design.md`, parser tests, and `ON_CAR_RUN_CARD.md` specify equipment, connection diagram, bench validation, capture limit, and abort/cleanup; test the parser before the car. Keep iAP2 Identification/Route Guidance distinct from CarPlay display/session negotiation; even a complete physical trace may be encrypted or opaque. **Rollback:** no vehicle changes in this step.

## 6. Obtain a protocol verdict only if static work leaves ambiguity (reviewed parked session)

**Context:** run only if Step 5 identifies a material question that static reconstruction cannot answer and a new capture method has been bench-validated and reviewed. Car is parked with factory wired CarPlay and Wi-Fi ADB; Mac wired ADB is not a dependency. The September 18 reconnect log is already captured and is not worth repeating unchanged. USB flash storage may receive bounded diagnostic output if needed, but no live receiver instrumentation is assumed safe.

**Tasks:** bench-check the chosen analyzer/capture chain before entering the car. Abort if its insertion changes baseline CarPlay connection, audio, charging, or stability. Capture a single known-state iPhone connect, Apple Maps route start, center Maps→Music switch, route end, and disconnect, with synchronized times and a physical cluster observation. Analyze offline: (1) Identification display/Route Guidance fields, (2) CarPlay display list, safe/view areas, stream setup and teardown, (3) whether the trace is complete enough to support a negative finding. Record raw and decoded artifacts with hashes under `research/captures/`. Do not force undocumented iPhone capability messages, inject USB traffic, remount, patch, or attach a tracer in this stage.

**Exit/verification:** either a byte-backed capability/session result with parser confidence, or a documented `unknown` with the precise visibility limit. A failed/partial trace does not count as proof that the iPhone or car lacks a feature. Aim for a 10–15 minute parked session with 1–5 minutes of actual capture; analyze afterward on the Mac. **Rollback:** remove analyzer/USB stick, return cabling/casting to baseline, verify ordinary CarPlay picture and voice.

## 7. Choose a supported implementation branch (Mac only)

**Context:** use Steps 1–6 evidence rather than assuming a capability plist or `InstrumentClusterDisplay=True` exists. Apple's public sessions establish the feature architecture, while actual negotiation fields/permission and receiver ABI must come from verified implementation evidence. Preserve existing center CarPlay and audio. The copied Honda proxy has a singleton screen callback; this is the first concrete ABI to model.

**ABI harness:** build `research/harness/receiver-abi/` on the Mac to mimic the observed Honda proxy's callback contract and a proposed per-stream interposer. Replay main/cluster initialize, properties, start, data, stop, and finalize in different orders. Assert that callbacks, buffers, and teardown never cross display identities, center video remains active when cluster stops, and no test path controls audio. Use copied-binary observations for the original ABI, not invented field layouts.

**Decision tree:**

1. If the *current* receiver already negotiates a second stream, document that path. Otherwise assess extending/interposing it. If that is infeasible, evaluate a verified MY16ADA-compatible newer receiver component and its Honda display/audio ABI bridge. If none exists, investigate building/porting independent receiver functionality while preserving Honda's existing authentication and audio behavior. Private protocol, compatibility, and licensing are feasibility gates; this escalation path is a commitment to investigate, not a claim that a port will work. Design two identified stream lifecycles: capability/view area, separate transport, callback dispatch instead of singleton storage, decode, bounded display-1 rendering, and independent teardown. CarPlay coexistence sizes the candidate but cannot establish protocol compatibility. Do not require today's one-screen receiver to negotiate two streams before *designing* a replacement; require actual second-stream setup before claiming success.
2. If a second stream is unavailable but actual iAP2 maneuver metadata is received, design a **Honda-drawn guidance** bridge with arrow, distance, road name, expiry, and lifecycle. Avoid factory setters that emit B-CAN; use a display-only bounded Navigation renderer. Clearly label this as guidance, not an iPhone-rendered map.
3. If neither protocol path is observable, keep the verdict `unknown` and identify the smallest new diagnostic. Do not promote OCR of the center image: Maps→Music removes its source.

**Exit/verification:** ABI harness tests pass, and `research/decisions/second-display-branch.md` contains an architecture diagram, ABI and failure analysis, updated simulator fixtures, candidate bill of materials, and go/no-go record referencing actual evidence. `unknown` remains an allowed result. **Rollback:** no vehicle change.

## 8. Prove a non-destructive recovery path (before receiver installation)

**Context:** the original backup is verified but boot-independent restoration is unproven. No receiver replacement, system remount, flash, or on-car injection can proceed until recovery is demonstrated. Deliberately breaking the live receiver to test rollback is prohibited.

**Tasks:** produce `research/recovery/BOOT_INDEPENDENT_RECOVERY.md` with exact image/file dependencies, access method when Android UI and ADB are unavailable, hashes, restoration sequence, and dry-run evidence. Validate on a spare/bench unit or with an independently documented hardware recovery mechanism for this exact head unit. If neither can be established without risking the live car, mark this gate blocked and keep receiver work offline. A backup hash alone is insufficient.

**Exit/verification:** reviewable boot-independent access and restoration evidence for the exact unit, or explicit `blocked`. **Rollback:** no induced live-car failure; this step creates documentation/test artifacts only.

## 9. Build one offline candidate against captured fixtures

**Context:** Step 7 selects a branch; Step 8 determines whether future receiver installation is even admissible. This step works on copied firmware and simulator fixtures only, even if recovery is still blocked.

**Tasks:** for the selected branch, put source/build output under `research/candidates/second-display/` and create `CHANGE_MANIFEST.md` listing every proposed changed file/package, original and candidate hashes, ABI changes, startup behavior, and failure modes. For an iPhone-video candidate, use distinct stream IDs and two independent teardown paths; for metadata fallback, keep it labeled Honda-rendered and avoid bus-emitting setters. Add tests that replay the captured exchange and center Maps→Music switch, reject stale frames, and preserve the original audio contract. Implement a display-1 renderer clipped to the calibrated Navigation rectangle. It must automatically release its experimental surface on stream stop, disconnect, process/window death, decoder error, or missing transport/session activity while the session is not deliberately paused. Start with a proposed 500–1000 ms transport-heartbeat timeout, then choose the value from observed transport cadence; **unchanged pixels are never a failure signal** because a map can be static. Verify Honda's normal Navigation view returns without a manual cleanup command. Prepare a reviewable synthetic renderer package/run card separately from any receiver package.

**Exit/verification:** reproducible offline build, fixture replay, independent proxy-callback tests, fail-clear timeout/process-death tests, byte-level change manifest, and exact proposed install/remove commands. Any private protocol field that cannot be established remains marked `unknown`, not hard-coded by guess. **Rollback:** delete only candidate build artifacts/working copies.

## 10. Validate a synthetic Navigation renderer on car (separate future approval)

**Context:** review the *exact* standalone synthetic-renderer APK, permissions, run card, timeout, and uninstall first. This is not a CarPlay receiver patch and cannot prove an iPhone stream. Step 8 recovery proof remains mandatory before Step 11's receiver installation.

**Tasks:** while parked, show bounded test frames only in the Navigation rectangle. Photograph the full physical cluster to verify speed, range, gauges, warning areas, and indicators stay visible. Trigger the prepared missing-heartbeat and process-stop paths; verify the experimental surface disappears and Honda's normal Navigation view returns. Stop immediately on occlusion, warning behavior, CarPlay audio loss, instability, or a failed watchdog. Uninstall and verify starting state. Do not touch vehicle buses or safety-related layers.

**Exit/verification:** physical photos/video, display-1 ownership, fail-clear timing, and exact uninstall/restoration. Synthetic pixels fitting safely do not authorize or prove receiver changes. **Rollback:** uninstall the exact package and verify normal Navigation, CarPlay picture, and voice.

## 11. Validate the receiver candidate on car (separate future approval)

**Context:** first live receiver experiment. It is blocked until Step 8 proves boot-independent restoration and Step 9 supplies a reviewed byte-level manifest and tested candidate. Approval of this plan or Step 10 does not approve Step 11. Investigate a runtime-only interposer/receiver launch that leaves boot and startup files unchanged and disappears after process restart or reboot. Prefer that for first negotiation if the old linker/process architecture permits it; if it does not, document why before proposing persistent replacement. A runtime-only experiment can still crash the receiver, so it retains the recovery and exact-approval gates.

**Tasks:** first document feasibility and exact launch/stop/cleanup for an ephemeral interposer without persistent startup edits. If feasible, review and run that form first; require successful negotiation, independent stream teardown, and reboot/restart cleanup before considering persistent installation. If infeasible, record the concrete linker/process limitation and review the more invasive candidate separately. For either form, review every changed file/package, original/candidate hash, ABI effect, startup impact, exact install commands, bounded parked run, abort criteria, and recovery method. Verify the iPhone negotiates a distinct cluster display/session/stream, center CarPlay and spoken voice remain normal, and decoded cluster-channel frames reach only the Navigation surface. Abort on warning, occlusion, instability, audio loss, or unexpected negotiation. Restore on failure with the reviewed method. Never modify the pristine backup.

**Exit/verification:** captured second-stream setup and provenance, output timing, physical placement, voice, fail-clear behavior, and restoration evidence. A capability flag or synthetic image alone does not pass. **Rollback:** prevalidated boot-independent restoration if Android/ADB fails, plus exact file/package restore for ordinary failures.

## 12. Accept Apple Maps, then test Waze (separate parked run)

**Context:** run only after Step 11 passes. Apple Maps is the primary goal; iPhone Waze may expose different cluster behavior and must be reported separately.

**Tasks:** with Apple Maps routing, switch center to Music and confirm live independent route/map updates in the physical cluster and audible directions. Test route end, disconnect/reconnect, app switch, stale heartbeat, and renderer recovery. Repeat with CarPlay Waze. Inspect full cluster photos for unobscured speed, range, gauges, indicators, and warnings; exercise the exact uninstall/restore path.

**Exit/verification:** Apple Maps passes only if a distinct iPhone cluster stream identity is tied to the displayed pixels, Music remains on center, voice works, lifecycle clears, factory content remains visible, and rollback restores the original behavior. State the Waze result separately. If protocol or hardware blocks the goal, report the blocker and closest proven fallback without calling it complete. **Rollback:** reviewed restoration procedure and package cleanup.

## Car-time packet and equipment list

There is **no new car task to approve this plan**. The next car session is the read-only storage/USB inventory in [the forensic run card](../acquisition/ON_CAR_FORENSIC_ACQUISITION_RUN_CARD.md). Bring the same FAT32/MBR USB with the existing backup, park and power the car, and connect the Mac over Wirebug Wi-Fi ADB (`192.168.86.102:5555` was the prior address). That session ends before bulk copying; its outputs set the exact acquisition size and commands for separate review. Later decoder coexistence or inline USB diagnostics require their own reviewed run cards. Do not restart CarPlay for ordinary logcat alone, and do not assume a full eMMC acquisition will fit a 10–15-minute window.

## Review questions and change control

The review feedback prioritizes the genuine iPhone-rendered map, accepts an inline analyzer only after bench validation shows normal CarPlay/MFi authentication, charging, audio, and reconnection, and targets 10–15-minute parked sessions. These are planning preferences, not proof that any analyzer will work on the Honda link or authorization for a particular on-car install.

Revise this plan when new evidence changes a gate. Keep a dated note of the evidence, changed decision, and affected later steps. Review approval permits Mac-side preparation; each temporary app install or receiver/firmware change still requires the exact artifact and run card to be reviewed first.
