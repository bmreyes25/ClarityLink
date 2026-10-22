# Agent task prompt template

Every task prompt for Claude Code or Codex in this repository must contain, or explicitly require, each item below. The authoritative wording is in [`AGENTS.md`](../../AGENTS.md); link to it, do not paraphrase it.

## Required contents

1. **Repository and baseline.** Repository URL, and an instruction to fetch and verify `origin/main`, the relevant PR heads and their ancestry live. Starting SHAs in a prompt are a dated snapshot, not a source of truth.
2. **Worktree and ownership.** A dedicated worktree and branch, the explicit file scope the task may change, and the owners of overlapping files (open PRs, other agents). Other agents' worktrees are not touched.
3. **Autonomous implementation.** Diagnose root causes, add regression tests, rerun affected checks. Stop only for destructive, safety-policy, or authorization decisions.
4. **Per-unit publication.** Each verified, public-safe unit is committed and pushed through `tools/publish_checkpoint.sh` (stacked work with `--stack-parent-pr`), the remote SHA verified with `tools/verify_remote_publication.py`, linked to a PR, with CI recorded. No blanket staging, force-push, or direct push to `main`.
5. **Public and private evidence.** Honda binaries, decompiled sources, captures, identifiers, credentials and signing material never enter Git. Public-safety gate and secret scan on the diff. Raw evidence that cannot be published is preserved privately with the blocker recorded.
6. **Review.** `@ECC` when callable. No fabricated approval, and no self-review or other-agent review recorded as an eligible human approval.
7. **Honda restrictions.** `safeForHonda() == false`. No Honda ADB, live iPhone, receiver patching, Xposed, display injection, CAN, firmware, authentication bypass, or vehicle testing unless a separate, written, task-specific authorization says otherwise.
8. **Honest results.** Synthetic, host-only, emulator and vehicle evidence are separate classes; an unavailable or skipped check is never reported as passed; a failed gate is reported as failed and its threshold is not changed to pass it.
9. **Final report.** Repository, branch, exact local and remote SHAs, PR URL, tests run with counts, CI/CodeQL state, review state, worktree cleanliness, unpublished commits, and remaining blockers.

## Skeleton

```
# <TASK-ID> — <title>
Role: <Claude implementation | Codex independent verification>
Repository: https://github.com/bmreyes25/ClarityLink
Baseline: verify live (dated snapshot: <sha> on <date>)
Scope: <files/areas the task owns>   Overlaps: <PRs/agents>
Objectives: <numbered, testable>
Acceptance: <exact gates; thresholds are not negotiable>
Rules: follow AGENTS.md (publication, stacking, public safety, review, Honda restrictions)
Deliverables: <docs, code, tests, handoff>
Final report: items 9 above
```
