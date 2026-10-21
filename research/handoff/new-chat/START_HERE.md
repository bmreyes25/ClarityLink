# ClarityLink — local Mac development session

Run ClarityLink development on the authorized Mac workspace. The only canonical repository is [bmreyes25/ClarityLink](https://github.com/bmreyes25/ClarityLink); do not use Codex Cloud or create another repository.

## First steps

1. Confirm the active checkout with `git rev-parse --show-toplevel`. Use the repository root as the Codex project folder, not this handoff directory.
2. Read `AGENTS.md`, `NEXT_ACTION.md`, `docs/status/current.md`, and `docs/status/milestones.json` from the active root.
3. Inspect the current GitHub branch and pull request state. Treat those live refs as authoritative; reports may contain historical commit IDs.
4. Inspect branch, upstream, worktree changes, ignored source-like files, and related worktrees before editing.
5. Work on a scoped feature branch and publish each approved development unit with `tools/publish_checkpoint.sh`. Verify the live remote SHA before reporting completion.

## Safety and local tools

REA, Ghidra, JADX, Android API 17 build tools, USB devices, and authorized private evidence stay local. Never publish credentials, raw or derived Honda artifacts, private evidence, or generated binaries. Keep `safeForHonda() == false`. Do not connect to a car or run Honda ADB as part of commit, push, CI, or publication.

See `README.md` in this directory for this handoff's contents and history.
