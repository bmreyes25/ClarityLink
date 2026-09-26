# Local model tasks after USB removal

Use a new local Codex task for each prompt. The existing long conversation exceeded the loaded 65,536-token context (67,057 input tokens). Start with file pointers rather than pasting the conversation or entire research tree. Keep each task limited to its named files; use short excerpts for native analysis. The advice-only `run_step.py` client is an alternative that builds bounded packets but does not execute its recommendations.

Working directory: `/Users/bmreyes24/ClarityLab/clarity-analysis`.

F-B is now verified complete for the reviewed scope; see `research/acquisition/ACQUISITION_COMPLETION_20260926.md`. The current analysis dataset is `/Users/bmreyes24/ClarityLab/forensic/CLARITY_FORENSIC_20260925_211500_COMPLETE_WORKING`. Its `COMPLETE_ORIGINAL` sibling is immutable. **Start implementation with Prompt 2.** Prompt 1 is optional independent review; do not repeat copying or ask for the car merely to recheck completed acquisition work.

The USB was flushed and unmounted on the head unit before removal. Storage completion is separate from SHA-256 verification on the Mac and completion of the eight labeled runtime states. Do not treat USB removal as a completed forensic acquisition. Originals, private captures, and raw firmware remain outside Git. Use only working copies for extraction and analysis. Each task ends with a compact handoff for Codex verification and a sanitized GitHub checkpoint, following `research/plans/STEP_COMPLETION_POLICY.md`.

## Prompt 1 — inspect the acquisition and find the next gate

> Work in `/Users/bmreyes24/ClarityLab/clarity-analysis`, offline. Read `research/plans/STEP_STATUS.md`, `research/plans/STEP_COMPLETION_POLICY.md`, `research/acquisition/FORENSIC_STATUS_20260925.md`, and only section F-B of `research/plans/CARPLAY_SECOND_DISPLAY_REVIEW.plan.md`. Inspect the current Mac acquisition manifests and verified copies without modifying originals; inspect the CLARITY USB only if it is still mounted. Establish which files have current Mac-side SHA-256 verification, whether all eight labeled runtime states exist and pass the declared checks, and whether a separate complete immutable Mac original has been made. Use paths literally; report absent paths rather than guessing. Do not create FINISHED.txt, change originals, overwrite the existing partial original or working directory, access ADB, or claim completion from STORAGE_DONE.txt. Write a concise gap report under research/local-model/runs. Report exact missing evidence and the next verification command for Codex. Stop at that gate.

## Prompt 2 — one simulator behavior

> Work in `/Users/bmreyes24/ClarityLab/clarity-analysis`, offline. Read `research/plans/STEP_STATUS.md`, `research/local-model/PROJECT_BRIEF.md`, `research/plans/STEP_COMPLETION_POLICY.md`, only Step 2 of the plan, and `research/simulator/INFOTAINMENT_TWIN_SCOPE.md`. Inspect the existing simulator and its tests. Use verified local working-copy evidence only; do not modify backup originals. Choose one missing display/service ownership fixture supported by the saved captures, add it with source provenance and one meaningful replay test, and preserve the distinction between observed Honda mirroring, observed head-unit Waze guidance, and hypothetical independent iPhone video. Check Maps-to-Music behavior, route end, disconnect, and stale clearing where relevant. No network, ADB, vehicle bus interface, or receiver patch. End with changed paths, test command/result, observed facts, unknowns, and the Codex verification gate. Do not mark the full Step 2 complete because one test passes.

## Prompt 3 — prepare the decoder diagnostic offline

> Work in `/Users/bmreyes24/ClarityLab/clarity-analysis`, offline. Read the compact project brief and status, the completion policy, only Step 3 of the plan, and the existing decoder-capacity probe source and run card. Explain why 28/30 frames is below 95%. Prepare one bounded background-safe diagnostic under research/probes/carplay-coexistence that would decode one additional 800x480 H.264 stream at 15 fps for 60 seconds behind active CarPlay. It must have no root, network, audio, overlay, bus, or vehicle permissions. Preserve drain/EOS timing and measure actual outputs, gaps, and errors; declare the 95% and 250-ms criteria and sensor-unavailable behavior. Prepare source, offline validation, exact artifact hash if build tools are available, and install/stop/uninstall run card. Do not install or execute anything on the car. End with a handoff for Codex verification and later separate on-car review.

## Prompt 4 — trace receiver Identification evidence

> Work in `/Users/bmreyes24/ClarityLab/clarity-analysis`, offline. Read the project brief and status, completion policy, only Step 5 of the plan, `research/native/receiver-multidisplay-audit.md`, and `research/NATIVE_CARPLAY_CLUSTER.md`. Select one unresolved Identification/capability function and trace its callers and data structures using the verified working binary and existing disassembly. Cite file SHA-256, symbol or offset, and the relevant instruction/data evidence. Separate main display registration, guidance metadata, independent video stream negotiation, and Ultra. Do not invent capability keys or infer packets from dumpsys/runtime snapshots. Save short evidence excerpts locally, and write a sanitized finding with observed/inferred/unknown labels. No original edits, ADB, patching, credential extraction, or upload of vendor/private artifacts. End with the next unresolved question and a Codex verification handoff.

## Advice-only terminal alternatives

Run one command at a time from the analysis root:

```sh
python3 research/local-model/run_step.py --step F-B --question "What verification gates remain before this acquisition can be declared complete?"
python3 research/local-model/run_step.py --step 2 --question "Identify one source-backed display ownership fixture to add next; distinguish observed and hypothetical behavior."
python3 research/local-model/run_step.py --step 3 --question "Identify the smallest remaining offline preparation task for the active-CarPlay coexistence probe."
python3 research/local-model/run_step.py --step 5 --question "Identify one unresolved Identification function and the exact evidence needed to resolve it offline."
```

These return advice, not executed work or verified results. Use `--show-prompt` to inspect the packet. Codex verifies each implementation before a dependent task advances and pushes only sanitized documentation/source.
