# Studio task worktree transaction

ClarityLink task work should start in a clean feature worktree based on the
fetched `origin/main`. The task guard records an exact file scope in that
worktree's Git administrative directory and reserves those paths across local
worktrees. Scope reservations coordinate participating agents; they do not
approve files for public release.

## Start and extend a task

Check readiness:

```sh
python3 tools/task_worktree_guard.py preflight --repo . --json
```

On a clean feature branch at current `origin/main`, declare each file path:

```sh
python3 tools/task_worktree_guard.py begin --repo . --task CL-EXAMPLE-01 \
  --file src/example.py --file tests/example/test_example.py
```

`begin` confirms canonical `origin`, unique branch ownership, a clean
worktree, and exact equality with the fetched `origin/main`; it records the
starting SHA and acquires exclusive path reservations. A task that needs more
files must review and add each path explicitly:

```sh
python3 tools/task_worktree_guard.py extend --repo . \
  --file src/new_component.py
```

Restricted/private roots, ignored paths, binary files, symlink paths, and
directory paths cannot be reserved. Never resolve a stale or mismatched
reservation by deleting it automatically; inspect its recorded task and
worktree owner first.

## Complete a task

Before completion, inspect the actual status and task-owned scope:

```sh
python3 tools/task_worktree_guard.py status --repo . --json
```

Review every file, run the relevant checks, then use
`tools/publish_checkpoint.sh` with individually listed files and
`--public-safe-reviewed`. The task guard does not stage, commit, push, or
declare content public-safe. After the scoped checkpoint is published and its
open PR points to the verified remote SHA, finish the transaction:

```sh
python3 tools/task_worktree_guard.py finish --repo . --pr 123
```

`finish` requires a clean worktree and live branch/PR SHA verification before
releasing reservations. Stop hooks block an active task transaction or an
unverified publication. A no-op task with no active scope can end only when
the existing publication audit reports a clean, synchronized branch.

Unknown ownership, failed checks, private evidence, and mismatched reservation
records remain preserved for explicit reconciliation; the guard never uses
Git cleanup commands or removes source files.
