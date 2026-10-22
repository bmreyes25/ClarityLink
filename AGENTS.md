# Repository workflow rules

These rules apply to every AI-agent campaign in this repository, whether run by Claude Code or Codex. This file is the single authoritative contract; `CLAUDE.md` is a short entrypoint that points here, and `docs/development/agent-task-prompt-template.md` is the checklist every task prompt must satisfy. Do not copy these rules into other documents: link to them.

## Autonomous Milestone Completion Policy

- At the beginning of every agent task, read this file; identify the active repository, branch, and worktree; fetch remote references; inspect current `origin/main`, local changes, untracked files, unpublished commits, related worktrees, existing commit/push/PR automation, and current GitHub rulesets/protection; and establish acceptance criteria. Preserve unrelated work.
- Establish acceptance criteria before implementation, then keep working after ordinary test failures, races, emulator timeouts, and review findings. Investigate root causes, add regression coverage, correct defects, and rerun affected checks instead of stopping at the first failure.
- Do not claim PASS without the required runtime evidence. Do not weaken mandatory tests or replace runtime proof with simulation or static validation.
- Commit every completed, verified development unit before ending the task. Use a descriptive message; do not create empty commits or mix unrelated changes. A missing reviewer does not prevent a verified local commit. If a genuine blocker prevents verification, preserve the work and report the blocker; use a clearly marked local WIP checkpoint only when safe, without claiming it passed.
- Stop only for a specific external blocker that prevents authorized progress; state the blocker and evidence while continuing independent work.
- Retain all project safety restrictions, including no Honda or live-iPhone operations and `safeForHonda() == false`.

## Campaign start and closeout

- At campaign start, record the repository path, worktree, local `HEAD`, branch, `git status --short --branch`, untracked files, unpublished commits, and relevant `origin` state. Fetch current remote references before using remote state as a baseline.
- Before finishing any task, report work completed; tests and results; final local commit SHA; branch and worktree; clean/dirty state; untracked and unpublished work; push status; PR URL; CI/CodeQL status; review status; and remaining blockers. Include `origin/main` when publication was requested. If a field cannot be verified, say so and explain why. Never finish with verified development work unsaved.
- If a field cannot be verified, say so and explain why. Do not substitute assumptions or stale receipts for current state.

## Development units and commits

- Complete each coherent development unit, run its relevant checks, verify the resulting diff is public-safe, and commit it before moving to unrelated work or ending the campaign.
- Do not claim a unit is tested unless the tests ran on the recorded commit or exact working tree. When verification is blocked, report the blocker and preserve the work; create a clearly marked local WIP checkpoint only when safe, without claiming it passed.
- Keep commits focused. Do not include local research, vehicle captures, credentials, generated artifacts, or unrelated checkout changes in public commits.
- Before committing, inspect staged paths and contents, check whitespace, and confirm the commit contains only the intended public-safe unit.

## Public source and private research

- Treat ignored status as a Git exclusion only; it is not evidence of backup, encryption, or safe deletion.
- Keep raw or derived vehicle data, private Honda evidence, credentials, signing material, and local research outside public Git. Never publish private Honda evidence.
- Do not perform Honda or vehicle operations. `safeForHonda()` must remain `false`.
- Review ignore rules whenever source or tests are added. Broad ignore patterns must have explicit, narrow exceptions for intended public source; verify with `git check-ignore -v` and `git ls-files` that important source is not hidden.
- If private test code or evidence is needed, keep it in an explicitly private location and document its runner/dependency boundary without copying private evidence into public source.

## Publication

- For tested, public-safe development changes, publication is part of task completion: inspect the complete staged diff, check for credentials and private data, run appropriate tests and security scans, commit verified changes, push an appropriate feature branch, and create or update the relevant PR. Do not wait for a separate request to push or open a PR. Reuse an appropriate existing PR. Inspect and follow current GitHub rulesets and protections; never bypass them. Verify the remote commit SHA and check GitHub Actions and CodeQL; investigate and address actionable failures.
- Never publish private Honda research, firmware, captures, credentials, identifying material, or a historical branch containing private data. If a branch contains such material, publish only a clean public branch based on the appropriate public base.
- Use `@ECC` when available and seek separate independent code and security reviews for relevant changes. Never claim independent approval or fabricate review results. If no actual independent reviewer is available, run available static checks and security scans, document the missing review, and do not merge changes that require mandatory independent review. Independently inspected, public-safe, tested synthetic laboratory work may be published to a non-merged feature branch and PR while review is outstanding. Missing independent review does not block a verified local commit.
- Never automatically merge Honda integration, receiver authentication or security, vehicle-control, factory-warning, or `safeForHonda()` changes; unverified or failing code; or historical branches containing private data. Keep auto-merge disabled for these categories and use the existing protected-main workflow. Do not weaken Honda safety gates.
- Never force-push, discard local work, remove worktrees, or delete research files as part of routine campaign cleanup.

## Mandatory local execution and GitHub checkpoints

- Execute ClarityLink work locally on the authorized Mac. REA/Ghidra/JADX, macOS development tools, Android API 17 build tools, USB/test equipment, and separately authorized private evidence remain local. Do not move development to Codex Cloud and do not create another repository.
- `origin` must identify `bmreyes25/ClarityLink`. Use the `gh` credential helper/Keychain-backed login; never put credentials in files, commands, or logs. Do not weaken sandboxing globally.
- Every coherent approved development unit must end with a live GitHub checkpoint before unrelated work begins. A local commit, clean worktree, or an agent's own report is not proof of publication. Verify `git ls-remote` SHA equals local `HEAD` using `tools/verify_remote_publication.py`.
- Use `tools/publish_checkpoint.sh` with explicit task ID, branch, file list, message, verification level, optional existing PR, and `--public-safe-reviewed` only after reviewing every scoped file. Never stage repository-wide. Review full staged content and classify ignored files before publication. The designated maintenance workflow alone may use `--maintenance-owner` for shared status files.
- `VERIFIED` requires a successful verification command. `WIP_UNVERIFIED` may be pushed only when its entire explicit scope is public-safe; this repository is public, so never include newly sensitive or restricted material. Clearly label WIP, do not create a PR for a first WIP, resume on the same branch, and never merge it automatically. Record failing or incomplete checks honestly.
- Never publish a WIP or any source whose public safety is uncertain. Preserve it locally and use an approved restricted backup; report that exception and blocker. No publish operation requires or triggers car access.
- Each concurrent agent session owns its own feature branch/worktree and explicit file scope. Do not switch to, update, or publish another session's branch. Do not routinely edit shared roadmap/status files; only a designated maintenance task reconciles canonical global status.
- Read actual remote ancestry before branch changes. Do not create speculative merges or rewrite history to make a branch appear current. Never force-push or push directly to protected `main`.
- A final PASS requires remote SHA verification. Every final development report includes repository, branch, local SHA, remote SHA, commit URL, PR URL (or none), tests, worktree status, unpushed commit count, uncommitted source count, and pending blockers. If any source or commit is unpublished, say so and do not report completion.
- `.codex/hooks.json` configures read-only SessionStart and Stop audits. The Stop hook may request another bounded turn but must never commit/push unknown files; honor `stop_hook_active` and report a blocker after the continuation has already been used. Hooks are not crash protection and run only after project trust approval in Codex Desktop.
- `tools/check_source_discovery.py` reports source-like files excluded by ignore rules. Review each result; never auto-add ignored files.
- Maintain `safeForHonda() == false`. Honda/ADB/vehicle use remains separately gated and owner-authorized; publication and CI must never connect to the car.

## Non-negotiable safety boundaries

- `safeForHonda()` must remain false.
- Do not perform automatic vehicle access, Honda ADB operations, authentication bypasses, firmware modifications, private display-control operations, or CAN transmission.
- Do not use destructive Git commands or reset/overwrite existing worktrees.

## Stacked work

- A branch that depends on another open PR is published through `tools/publish_checkpoint.sh --stack-parent-pr N`. The tool reads the parent live and refuses unless the parent is open, not from a fork, based directly on `main`, free of merge conflicts, and its live branch SHA equals the PR head; the commits between `origin/main` and the parent head must equal the commits the parent PR shows; the new branch must start exactly at that head and descend from the current `origin/main`. It records `Stacked-On` in the commit and bases the new PR on the parent's branch. Never seed a branch with a plain push of someone else's history to get around this check.
- A stacked PR does not trigger the `main`-based required checks. Validate the exact head and the exact final merge result before integration; a stale run is never evidence for a new SHA. Do not change a PR's base repeatedly to force CI.

## Publication candidates and public safety

- Offline CI runs `tools/check_public_safety.py` on every pull request to `main`; `tools/publish_checkpoint.py` runs it on the staged content. A pass means none of its checks failed; it is not a review. See `docs/security/public-safety-gate.md`.
- PR titles are one short line. Put the explanation in the body.

## Review

- Use `@ECC` when a callable independent review capability exists. Never record an AI agent's review, another agent's review, or a self-review as an eligible human approval, and never record an approval that did not happen. When no independent reviewer exists, say so.
