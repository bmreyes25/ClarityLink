# ClarityLab: CarPlay navigation for the 2018 Honda Clarity cluster

This project investigates how to show **Apple Maps or Waze navigation from an iPhone in the factory instrument cluster** while the center display remains independently usable for Music, calls, or other CarPlay apps. The target is genuine CarPlay instrument-cluster integration: a separate map stream and, where available, maneuver, distance, and road guidance. Normal spoken navigation through the factory speakers must keep working.

The vehicle is a 2018 Honda Clarity with an MY16ADA head unit running Android 4.2.2, build 1.F1A2.45. Work is evidence-first and begins with copied firmware, parked read-only diagnostics, and a Mac infotainment twin. No receiver patch or independent iPhone-rendered cluster map is working yet.

## What we have established

- The head unit exposes separate 800×480 Android center and HDMI display devices. Honda Hack can mirror live CarPlay into the cluster's central Navigation area. Apple Maps voice guidance continued to work during that cast. When the center switched to Music, the cast followed Music; it was a mirror, not a separate iPhone map.
- Waze running **on the head unit** drove a native cluster arrow and distance that remained visible over Honda Home and cleared when the route ended. This proves a separate cluster navigation view exists, but it does not prove that iPhone CarPlay sends route guidance to this Honda receiver.
- Static receiver analysis identified the `jmcs` CarPlay engine, `libcarplay_proxy.so`, CarPlay service, Honda Navigation/ExternalDisplay services, and the second-display rendering path. The inspected build configures one main CarPlay screen; the proxy's screen callback is a singleton. A dormant usable second stream has not been demonstrated.
- A temporary, approved decoder probe exercised two NVIDIA H.264 instances and was removed afterward. It produced frames from both, but did not establish sustained concurrent decoding **with CarPlay running**. iAP2 identification packets and actual multi-display negotiation have not been decoded.
- A Mac simulator replays observed casting and head-unit Waze behavior alongside clearly labeled hypothetical independent-screen and route-metadata contracts. It tests lifecycle behavior such as Maps-to-Music switching, route end, disconnect, and stale guidance clearing; it is not a full Tegra or cluster-electronics emulator.
- The reviewed **head-unit-only** forensic acquisition is complete: eight eMMC chunks, eight MTD images, eight filesystem archives, kernel/HAL metadata, and eight labeled runtime states. All 2,487 final checksum entries passed in separate new Mac original/working copies. The original is read-only; older backups were preserved. The 7,549,747,200-byte eMMC reconstruction and nine-partition GPT checks passed. Optional protected process reads are explicitly unavailable; the live dataset is not atomic or proof of boot-independent recovery. See [completion evidence](research/acquisition/ACQUISITION_COMPLETION_20260926.md).
- A local Ollama research profile uses the installed `qwen3.6:35b-coding` at a tested 65,536-token context. It receives short, line-numbered step packets from curated sanitized files. It cannot execute car commands; its suggestions are checked against the evidence and tests.
- Step 3 has begun offline with a trace scorer for a future active-CarPlay decoder test. It correctly treats 28/30 as 93.33%, below the planned 95% gate, and keeps picture/voice observations separate from decoder timing. No new diagnostic APK or live coexistence test has been run.

The detailed [analysis report](research/REPORT.md) separates observations from inference. The [native cluster audit](research/NATIVE_CARPLAY_CLUSTER.md) explains the route-metadata and separate-video paths. The [execution plan](research/plans/CARPLAY_SECOND_DISPLAY_REVIEW.plan.md) and [step-status index](research/plans/STEP_STATUS.md) record progress and evidence gates. The [forensic status](research/acquisition/FORENSIC_STATUS_20260925.md), [resume run card](research/acquisition/RESUME_RUN_CARD_20260925.md), and [local-model setup](research/local-model/README.md) describe the next work.

## Next milestones

1. Use the new verified complete working copy for offline research; the acquisition and Mac-copy checkpoint has passed. Start a fresh local task with [the bounded prompts](research/local-model/POST_ACQUISITION_PROMPTS.md), preserving every original backup.
2. Feed verified firmware and existing captured fixtures into the Mac twin; map receiver, display, audio, and navigation boundaries. A sanitized nine-partition GPT/mount fixture already seeds the firmware-catalog layer.
3. Determine from actual protocol evidence whether the Honda advertises iAP2 route guidance or negotiates multiple CarPlay displays. Separately test decoder coexistence with the main CarPlay session.
4. Prototype the smallest reversible display-only integration that survives center app changes, route end, and disconnect while preserving voice. A true independent iPhone-rendered map requires proven receiver support or a separately reviewed receiver change.

CarPlay Ultra and spatial audio are later research topics; neither is a claim of support on this hardware.

## Safety and data handling

No system flash, partition write, remount, CAN/ADAS/safety-system access, or vehicle-control change is part of the current work. Any later on-car modification requires an exact artifact, backup/recovery evidence, rollback procedure, and separate review. The pristine backup, raw firmware, private logs, phone/route data, generated APKs, and forensic images stay local and are excluded from this repository. Only sanitized research, source, fixtures, plans, and tests are tracked.

This repository is private because reverse-engineering notes and vehicle-specific details need review before any broader release.
