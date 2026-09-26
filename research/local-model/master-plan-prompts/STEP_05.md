# Master plan Step 5: Reconstruct Identification statically and design any missing capture

**Assigned model: Ollama local model — Mac only; future car capture handled by GPT-6 Sol Codex.**

Copy this entire file into a fresh tool-capable task.

## Assigned work

Analyze copied `jmcs`, configs and receiver libraries. Trace configuration/screen initialization into iAP2 Identification serialization and, separately, CarPlay display/session negotiation. Keep Identification, route-guidance metadata and video-session setup distinct. Record reproducible source SHA256, function/symbol or virtual address, derivation, encoding, current behavior, likely purpose, confidence and missing proof in `research/protocol/static-identification.md`.
Build a tested current one-screen serialization fixture only for fields actually reconstructed. Label its bytes predicted/static, never wire-observed; unknown bytes/fields remain explicit unknowns. Ordinary dumps/logcat/screenshots/wired ADB do not reveal raw Identification payload; a USB stick is storage, not an inline sniffer. Existing kernel usbmon support is absent; do not repeat ordinary captures expecting payloads.
If material uncertainties remain, create `research/protocol/capture-design.md`: candidate inline analyzer requirements (roles/topology, speed, power, cables, full payload/export, pass-through/MFi authentication), bench validation, bounded car run card and cleanup; or a future narrowly scoped trace requiring exact review plus boot-independent recovery; or static-only unknown. No purchases or live tracing/patches now. If a concrete capture format is selected, implement/test a parser preserving framing, checksums, unknown fields, timestamps and provenance; account for encrypted/opaque traffic. Give all future car actions to GPT-6 Sol Codex. Exit: reproducible known/unknown table and tested justified fixture, with unresolved capture work explicitly gated. Step 5 can run offline while Step 4 remains pending; it cannot declare Step 4 complete.

## Execution rules

You are working in `/Users/bmreyes24/ClarityLab/clarity-analysis`. Read `AGENTS.md` if present, `research/local-model/PROJECT_BRIEF.md`, `research/plans/STEP_STATUS.md`, `research/plans/STEP_COMPLETION_POLICY.md`, and ONLY this numbered section of `research/plans/CARPLAY_SECOND_DISPLAY_REVIEW.plan.md`. Inspect existing work before editing; do not redo completed work. F-A/F-B are separate completed acquisition phases, not Steps 1–5.

Never modify either pristine dataset:
- `/Users/bmreyes24/ClarityLab/backups/CLARITY_BACKUP_20260918_0225_ORIGINAL`
- `/Users/bmreyes24/ClarityLab/forensic/CLARITY_FORENSIC_20260925_211500_COMPLETE_ORIGINAL`

Use `/Users/bmreyes24/ClarityLab/forensic/CLARITY_FORENSIC_20260925_211500_COMPLETE_WORKING` as the local analysis input. Before modifying any firmware/configuration, make a separate per-step derivative under ignored `research/tmp/step-N/`; hash source and derivative, preserve the baseline, and record a reversible diff. Do not duplicate whole images unnecessarily. Verify exclusions first. Keep raw firmware, archives, private captures, credentials, identifiers, and routes local and out of Git and remote AI services. Source/document edits belong inside the analysis repository. No vehicle system patches, flashing, writable remounts, protection changes, or safety/vehicle-bus operations.

Use actual local shell/file tools if available. Plain Ollama chat and `run_step.py` are advice-only: if tools are unavailable, provide a bounded handoff and explicitly say no commands were executed. Never fabricate findings, tests, commits, or pushes.

## Context and work budget

Use a fresh task, not this project's long conversation. The configured local model is `clarity-research:latest` based on `qwen3.6:35b-coding`, with 65,536 context tokens and a 4,096 response cap. Target at most about 16,000 initial input tokens; character estimates are approximate. Read targeted `rg` hits and short function excerpts, not entire archives, disassembly, or logs. Persist evidence and a concise handoff after each bounded milestone; start a fresh task when context fills. Keep observed, inferred, synthetic, and unknown evidence separate. Work only on the assigned step; dependencies can remain explicitly pending.

## Required end-of-step checkpoint

Create/update `research/progress/STEP_05_CHANGELOG.md` (replace N with this step number). Include UTC time, starting Git HEAD, files changed and purpose, source references/hashes where relevant, actual commands and exit/results, test counts, findings/confidence, limitations, rollback, outstanding gates, and next action. Keep private artifacts in ignored locations and cite sanitized references. Update `STEP_STATUS.md` and the relevant report/run card accurately. Never mark a partial or unverified step complete.

Run meaningful checks against the declared exit criteria. Prepare an evidence handoff for independent supervising Codex verification; if it has not happened, label acceptance pending Codex review. Do not advance a dependent gate based on the local model's own claim. A sanitized pending/failure checkpoint is still useful.

Inspect `git status`, `git diff`, the existing origin URL, and ignore rules. The intended private remote is `https://github.com/bmreyes25/clarity-carplay-cluster.git`. Stage only explicitly reviewed source/docs/tests; never `git add .`, raw data, or secrets. Inspect staged content and size. Commit a descriptive checkpoint and push without force. Preserve unrelated user changes; stop if credentials, divergence, or unexpected remote prevent a safe push. Verify the pushed commit using `git ls-remote origin refs/heads/main` against the intended local commit; do not assume push succeeded. Report commit SHA, remote verification, detailed changelog path, checks and remaining gates. Put the resulting commit SHA in the final handoff rather than trying to embed a commit's own SHA inside itself. If no changes are needed, report the existing verified checkpoint instead of an empty commit.
