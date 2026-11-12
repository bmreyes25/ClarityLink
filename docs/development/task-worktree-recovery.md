# Studio task worktree recovery

## Publication readiness

Run `python3 tools/task_worktree_guard.py preflight --repo . --base main --json`
before reserving files. For a stacked continuation, pass the literal base
branch that is the exact head of an open same-repository PR. `begin` repeats
this check before creating the manifest or reservations. The task worktree
must be clean and its `HEAD` must equal the fetched remote base. A task with
unpublished history cannot enter a new checkpoint through the normal path.

## Legacy task recovery

`tools/recover_legacy_task.py` supports a historical task only when its owner,
manifest, starting commit, complete commit path set, dirty path set, and
reservations can all be verified. It refuses merge history, out-of-scope or
untracked paths, an already published source branch, stale target bases,
unrelated source commits, and patches that do not apply cleanly to an isolated
copy of the target.

### Prepare

Create a clean managed feature worktree at the exact remote base. The base may
be `main` or the exact head of an open same-repository PR. Then prepare a
private provenance receipt and a validated patch plan:

```sh
python3 tools/recover_legacy_task.py prepare \
  --source-worktree /path/to/legacy-task-worktree \
  --target-worktree /path/to/clean-continuation-worktree \
  --target-task CL-EXAMPLE-CONTINUATION \
  --base codex/open-pr-head
```

Preparation does not change the source branch, task manifest, or reservations.
The receipt and exact source patch are stored with restrictive permissions in
the repository's Git administrative directory, outside the checkout. The
receipt records the source/target identities, starting and head commits,
scope, source hashes, conflict-probe result, and any overlapping paths. The
receipt is immutable; the separate private state file records transaction
progress.

### Commit the transfer

Review the prepared path and overlap inventory. The task owner must explicitly
authorize the exact source and target task IDs:

```sh
python3 tools/recover_legacy_task.py commit \
  --repo /path/to/clean-continuation-worktree \
  --transaction <prepared-transaction-id> \
  --owner-authorization '<owner_authorization value returned by prepare>'
```

The prepared authorization statement binds the source and target task IDs to
the transaction ID, target branch, exact target starting SHA, and immutable
receipt hash. A statement from a different prepared target cannot authorize
this transfer.

The operation rechecks both worktrees and the remote base, applies the exact
scoped delta with Git's three-way patching, and transfers all source
reservations under the shared Studio scope lock. It marks the source task as
transferred and creates the target task manifest. The source worktree and
commits remain unchanged. Repeating `commit` resumes an interrupted transfer
or reports the already completed transfer; it does not apply the patch twice.

The continuation uses the ordinary task publication workflow and publisher.
Reservations are released only by the normal `finish` path after the published
remote commit and open PR head match exactly. A publication failure leaves the
continuation task and its reservations in place for repair.

## Recovery boundaries

This operation does not resolve semantic conflicts, alter the publisher's
base-history rules, push or merge a PR, or approve publication. A conflict or
ambiguous ownership requires investigation and a new prepared transaction.
Never edit task manifests or reservation files by hand. Preserve the source
worktree and private receipt until publication and ordinary task completion
are verified.
