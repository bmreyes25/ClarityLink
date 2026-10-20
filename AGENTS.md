# Repository workflow rules

These rules apply to every Codex campaign in this repository.

## Autonomous Milestone Completion Policy

- Establish acceptance criteria before implementation, then keep working after ordinary test failures, races, emulator timeouts, and review findings. Investigate root causes, add regression coverage, correct defects, and rerun affected checks instead of stopping at the first failure.
- Do not claim PASS without the required runtime evidence. Do not weaken mandatory tests or replace runtime proof with simulation or static validation.
- Commit each verified, public-safe development unit continuously. Obtain separate read-only ECC code and security reviews, resolve actionable findings, and publish through the protected-main pull-request workflow when authorized.
- Stop only for a specific external blocker that prevents authorized progress; state the blocker and evidence while continuing independent work.
- Retain all project safety restrictions, including no Honda or live-iPhone operations and `safeForHonda() == false`.

## Campaign start and closeout

- At campaign start, record the repository path, local `HEAD`, branch, `git status --short --branch`, untracked source files, unpublished commits, and the `origin` GitHub state relevant to the work.
- Before finishing, report the final local `HEAD`, dirty status, untracked source files, unpublished commits, tests run and their results, and GitHub publication state (including PR and `origin/main` when publication is requested).
- If a field cannot be verified, say so and explain why. Do not substitute assumptions or stale receipts for current state.

## Development units and commits

- Complete each coherent development unit, run its relevant tests, verify the resulting diff is public-safe, and commit it before moving to unrelated work or ending the campaign.
- Do not claim a unit is tested unless the tests ran on the recorded commit or exact working tree. When tests cannot run, report the blocker and keep the unit uncommitted until it is tested, unless the user explicitly directs otherwise.
- Keep commits focused. Do not include local research, vehicle captures, credentials, generated artifacts, or unrelated checkout changes in public commits.
- Before committing, inspect staged paths and contents, check whitespace, and confirm the commit contains only the intended public-safe unit.

## Public source and private research

- Treat ignored status as a Git exclusion only; it is not evidence of backup, encryption, or safe deletion.
- Keep raw or derived vehicle data, private Honda evidence, credentials, signing material, and local research outside public Git. Never publish private Honda evidence.
- Do not perform Honda or vehicle operations unless the user separately authorizes a specific operation. `safeForHonda()` must remain `false` unless a separately reviewed, authorized change explicitly changes that requirement.
- Review ignore rules whenever source or tests are added. Broad ignore patterns must have explicit, narrow exceptions for intended public source; verify with `git check-ignore -v` and `git ls-files` that important source is not hidden.
- If private test code or evidence is needed, keep it in an explicitly private location and document its runner/dependency boundary without copying private evidence into public source.

## Publication

- Publish only reviewed, public-safe commits. For a requested publication, use a temporary branch and PR, verify the published commit and resulting `origin/main`, then report the exact SHAs and GitHub state.
- Never force-push, discard local work, remove worktrees, or delete research files as part of routine campaign cleanup.
