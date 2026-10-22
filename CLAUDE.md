# Claude Code entrypoint

The rules for this repository are in [`AGENTS.md`](AGENTS.md). They apply to Claude Code and to Codex equally; read that file first and follow it. Do not restate its rules here.

In short, and only as a pointer: work in your own worktree on your own branch; keep `safeForHonda() == false` and do nothing against the vehicle, a live iPhone or Honda software; publish every verified, public-safe unit through `tools/publish_checkpoint.sh` and verify the remote SHA with `tools/verify_remote_publication.py`; keep private evidence out of Git; use `@ECC` when callable and never record an approval that did not happen.

Writing a task prompt for an agent: start from [`docs/development/agent-task-prompt-template.md`](docs/development/agent-task-prompt-template.md).
