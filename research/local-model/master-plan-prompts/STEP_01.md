# Master plan Step 1: Create/audit Git and evidence baseline

**Assigned model: Ollama local model — Mac only.**

Copy this entire file into a fresh tool-capable task.

## Assigned work

Audit the existing baseline; Step 1 is already recorded complete, so reconcile evidence instead of recreating Git or backups. Check tracked files/ignore rules for firmware/private material and confirm backup protection without changing originals. Inventory receiver/config source references, captures, original hashes, historical decoder uninstall evidence, simulator checks, and Honda Hack settings. Follow the plan's evidence-ledger location (create it if absent): claims, artifact reference, observed/inferred status, confidence, and missing proof. Record known single-screen call sites/singleton offsets only with binary evidence. Photo-derived navigation bounds must include uncertainty; partition maps cannot establish display geometry. Run the existing relevant simulator checks. Exit: accurate baseline, intended tracked content only, reproducible evidence references and actual test results. If historical claims cannot be verified, mark them unknown rather than assuming completion.

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

Create/update `research/progress/STEP_01_CHANGELOG.md` (replace N with this step number). Include UTC time, starting Git HEAD, files changed and purpose, source references/hashes where relevant, actual commands and exit/results, test counts, findings/confidence, limitations, rollback, outstanding gates, and next action. Keep private artifacts in ignored locations and cite sanitized references. Update `STEP_STATUS.md` and the relevant report/run card accurately. Never mark a partial or unverified step complete.

Run meaningful checks against the declared exit criteria. Prepare an evidence handoff for independent supervising Codex verification; if it has not happened, label acceptance pending Codex review. Do not advance a dependent gate based on the local model's own claim. A sanitized pending/failure checkpoint is still useful.

Inspect `git status`, `git diff`, the existing origin URL, and ignore rules. The intended private remote is `https://github.com/bmreyes25/clarity-carplay-cluster.git`. Stage only explicitly reviewed source/docs/tests; never `git add .`, raw data, or secrets. Inspect staged content and size. Commit a descriptive checkpoint and push without force. Preserve unrelated user changes; stop if credentials, divergence, or unexpected remote prevent a safe push. Verify the pushed commit using `git ls-remote origin refs/heads/main` against the intended local commit; do not assume push succeeded. Report commit SHA, remote verification, detailed changelog path, checks and remaining gates. Put the resulting commit SHA in the final handoff rather than trying to embed a commit's own SHA inside itself. If no changes are needed, report the existing verified checkpoint instead of an empty commit.
