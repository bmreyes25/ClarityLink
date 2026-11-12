# Task worktree transaction recovery

`task_worktree_guard.py recover-finish --repo . --pr <number>` is a narrowly
scoped recovery for a task manifest whose `base` was recorded as its own
feature branch. It does not repair general manifest corruption and does not
provide a way to release reservations manually.

The recovery verifies the canonical repository, unique branch/worktree owner,
clean task worktree, exact reservation ownership, immutable starting SHA
ancestry, committed file scope, exact remote branch SHA, open same-repository
PR head and actual base, base ancestry, and the normal publication verifier.
For a stacked PR, the base must be the head of another open same-repository PR.
The command records a private audit event in the Git administrative directory,
atomically changes only the manifest base and PR binding, then calls the
ordinary `finish` path. Reservations are released only if that final ordinary
completion check succeeds. If a check fails, task ownership and reservations
remain for manual, evidence-based reconciliation.

Do not use this command to repair ambiguous ownership, a changed starting SHA,
source changes outside the reservation, an unpublished or mismatched branch,
a closed/cross-repository PR, or an unverified base. Do not edit task manifests
or reservation files by hand. Preserve the worktree and investigate the
specific failed check.
