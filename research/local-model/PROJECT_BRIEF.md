# ClarityLab local-model brief

Goal: make an independent, iPhone-rendered Apple Maps cluster view persist while Music is on the center display, with voice guidance intact and automatic cleanup. Test Waze separately. A Honda-drawn arrow/distance is a fallback, not proof of native CarPlay second-display support.

Observed: Honda Hack mirroring follows center-screen Maps→Music. Head-unit Android Waze can show an independent cluster arrow and distance, but its ordinary view omits road name. Two 800×480 diagnostic decoders produced 28/30 frames each with CarPlay disconnected; coexistence with active CarPlay remains untested. Static receiver review found a main-screen registration and singleton screen callback. Raw iAP2 Identification/Route Guidance payloads have not been captured.

Existing offline simulator assets already replay paired Maps/Music HDMI screenshots, head-unit Waze arrow/distance behavior, route end, and disconnect; proposed second-stream and metadata examples are labeled synthetic. Improve those fixtures and lifecycle assertions without waiting for a new capture. Ordinary Android runtime snapshots help with process/display/audio state but do not reveal raw iAP2 payloads.

Storage GPT partition names/sizes/mounts are useful for the firmware catalog only. They contain no cluster pixel boundaries or HDMI safe-area coordinates. Use saved display captures and physical photos for display geometry, with unmeasured edges still labeled unknown.

Step 3 now has a Mac-only trace scorer for a future active-CarPlay decoder test. It correctly marks 28/30 as 93.33% and below the 95% gate; 29/30 is the minimum passing count at that sample size. The historical signed probe was not changed. No new APK or live coexistence result exists.

Forensic state, September 26 UTC: F-B is complete for its reviewed scope. Initial USB storage verification passed 57 entries and eight tar structures; finalization added eight labeled runtime states and retained audit metadata. The final 2,487 checksum entries passed in both new Mac copies. Optional `/proc` maps/fd reads were permission denied in 158 attempts and are recorded unavailable. The reconstructed working image is 7,549,747,200 bytes; both GPT headers and entry arrays validate across nine partitions. `/data` tar warnings are five ignored Unix sockets. Historical partial copies and the September 18 pristine backup were preserved. No new storage acquisition is needed. Raw snapshots do not prove independent iPhone video, decoder coexistence, or iAP2 Identification bytes.

Current analysis source: `/Users/bmreyes24/ClarityLab/forensic/CLARITY_FORENSIC_20260925_211500_COMPLETE_WORKING`. Its separate `CLARITY_FORENSIC_20260925_211500_COMPLETE_ORIGINAL` sibling is immutable with zero write bits and must never be changed. The older `CLARITY_FORENSIC_WORKING` is historical and lacks the resumed additions; do not mistake it for the current complete dataset. All new analysis outputs belong under `clarity-analysis/research` or the new complete working copy, never an original.

Safety: do not patch, remount, flash, alter safety systems or vehicle buses. The current phase is offline analysis and simulator/probe preparation. A later reviewed acquisition may write only new files beneath the forensic USB sibling; Honda internal storage remains read-only source media. A full eMMC image does not prove a boot-independent recovery path. Raw images, phone data, routes, credentials, and vendor firmware remain local and outside Git.

Workflow: use the 12-step plan as a dependency graph. Work on one step and its exit criteria at a time. Label any hypothetical CarPlay protocol field as unknown until tied to observed bytes or copied-binary evidence. Show source path/line for factual claims. A local model response is advice; verify with scripts/tests and human review before car use.

After every step, Codex must preserve verified backups, check actual exit evidence, update sanitized documentation and status, commit/push to the private GitHub repo, and verify the pushed commit. See `research/plans/STEP_COMPLETION_POLICY.md`. Never mark completion based only on a model response, user report, exit code, or marker.
