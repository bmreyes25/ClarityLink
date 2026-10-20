# Offline blocker-resolution workflow

Use this process for normal offline engineering blockers. It does not authorize vehicle, phone, or emulator activity.

1. Read [current status](../status/current.md), the blocker entry, and its source evidence.
2. Record exact checkout, branch/HEAD, clean/dirty state, artifact hashes, and relevant tool versions before changing anything. Preserve untracked evidence and ignored artifacts.
3. State the smallest reproducible failure and the expected behavior. Separate observed facts, inference, and unknowns.
4. Define a bounded offline reproduction using synthetic fixtures where possible. Set explicit stop conditions before execution.
5. Change only the active milestone's scope. Keep compatibility and safety gates fail-closed; do not weaken checks to make a run pass.
6. Re-run targeted checks, the configured offline suite when applicable, repository health, and `git diff --check`. Record passes, failures, skips, and unrun checks.
7. Update the evidence report, status manifest, blocker list, and next action together. Link exact evidence and preserve the earlier result.
8. Request independent review of the exact change set and hashes. Address correctable findings and request re-review.
9. Stop if progress requires unknown-target ADB, private evidence, live iPhone/Honda access, hardware authority, installation, destructive repository operations, or a scope change. Ask for the missing evidence or authorization only after completing independent offline work.
