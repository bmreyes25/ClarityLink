# Repository workflow rules

These rules apply to every Codex campaign in this repository.

## Autonomous Milestone Completion Policy

- At the beginning of every Codex task, read this file; identify the active repository, branch, and worktree; fetch remote references; inspect current `origin/main`, local changes, untracked files, unpublished commits, related worktrees, existing commit/push/PR automation, and current GitHub rulesets/protection; and establish acceptance criteria. Preserve unrelated work.
- Establish acceptance criteria before implementation, then keep working after ordinary test failures, races, emulator timeouts, and review findings. Investigate root causes, add regression coverage, correct defects, and rerun affected checks instead of stopping at the first failure.
- Do not claim PASS without the required runtime evidence. Do not weaken mandatory tests or replace runtime proof with simulation or static validation.
- Commit every completed, verified development unit before ending the task. Use a descriptive message; do not create empty commits or mix unrelated changes. A missing reviewer does not prevent a verified local commit. If a genuine blocker prevents verification, preserve the work and report the blocker; use a clearly marked local WIP checkpoint only when safe, without claiming it passed.
- Stop only for a specific external blocker that prevents authorized progress; state the blocker and evidence while continuing independent work.
- Retain all project safety restrictions, including no Honda or live-iPhone operations and `safeForHonda() == false`.

## Campaign start and closeout

- At campaign start, record the repository path, worktree, local `HEAD`, branch, `git status --short --branch`, untracked files, unpublished commits, and relevant `origin` state. Fetch current remote references before using remote state as a baseline.
- Before finishing any task, report work completed; tests and results; final local commit SHA; branch and worktree; clean/dirty state; untracked and unpublished work; push status; PR URL; CI/CodeQL status; review status; and remaining blockers. Include `origin/main` when publication was requested. If a field cannot be verified, say so and explain why. Never finish with verified development work unsaved.
- If a field cannot be verified, say so and explain why. Do not substitute assumptions or stale receipts for current state.

## Approved research-tool recovery

- Before specialized offline research, verify required approved development tools and their pinned versions. Where task authorization permits, recover missing standard tools from trusted official sources, verify integrity, preserve existing configuration, and test actual functionality. Do not infer blanket permission to install arbitrary executables. Escalate only genuine external, privileged, security, or authorization blockers; continue independent work.

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

## Non-negotiable safety boundaries

- `safeForHonda()` must remain false.
- Do not perform automatic vehicle access, Honda ADB operations, authentication bypasses, firmware modifications, private display-control operations, or CAN transmission.
- Do not use destructive Git commands or reset/overwrite existing worktrees.
