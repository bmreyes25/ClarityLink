# ClarityLab local-model brief

Goal: make an independent, iPhone-rendered Apple Maps cluster view persist while Music is on the center display, with voice guidance intact and automatic cleanup. Test Waze separately. A Honda-drawn arrow/distance is a fallback, not proof of native CarPlay second-display support.

Observed: Honda Hack mirroring follows center-screen Maps→Music. Head-unit Android Waze can show an independent cluster arrow and distance, but its ordinary view omits road name. Two 800×480 diagnostic decoders produced 28/30 frames each with CarPlay disconnected; coexistence with active CarPlay remains untested. Static receiver review found a main-screen registration and singleton screen callback. Raw iAP2 Identification/Route Guidance payloads have not been captured.

Existing offline simulator assets already replay paired Maps/Music HDMI screenshots, head-unit Waze arrow/distance behavior, route end, and disconnect; proposed second-stream and metadata examples are labeled synthetic. Improve those fixtures and lifecycle assertions without waiting for a new capture. Ordinary Android runtime snapshots help with process/display/audio state but do not reveal raw iAP2 payloads.

Storage GPT partition names/sizes/mounts are useful for the firmware catalog only. They contain no cluster pixel boundaries or HDMI safe-area coordinates. Use saved display captures and physical photos for display geometry, with unmeasured edges still labeled unknown.

Forensic state, 2026-09-25: the USB sibling `CLARITY_FORENSIC_20260925_211500` has verified SHA-256 for eight eMMC chunks (7,549,747,200 bytes), eight MTD images, `/system.tar`, and seven metadata files. The primary and backup GPT headers and partition-entry CRCs validate; there are nine named eMMC partitions. Seven planned filesystem archives, the broad metadata inventory, eight runtime snapshots, `STORAGE_DONE.txt`, and `FINISHED.txt` are missing. This is a verified **partial** acquisition. A separate original 2026-09-18 backup remains untouched and read-only. Never call the new dataset complete until the missing requirements are met or the scope is explicitly revised.

Safety: do not patch, remount, flash, alter safety systems or vehicle buses. The current phase is offline analysis and simulator/probe preparation. A later reviewed acquisition may write only new files beneath the forensic USB sibling; Honda internal storage remains read-only source media. A full eMMC image does not prove a boot-independent recovery path. Raw images, phone data, routes, credentials, and vendor firmware remain local and outside Git.

Workflow: use the 12-step plan as a dependency graph. Work on one step and its exit criteria at a time. Label any hypothetical CarPlay protocol field as unknown until tied to observed bytes or copied-binary evidence. Show source path/line for factual claims. A local model response is advice; verify with scripts/tests and human review before car use.
