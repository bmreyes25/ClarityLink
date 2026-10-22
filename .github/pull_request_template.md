## Task and owner

<!-- Task ID, purpose, and the agent or person who owns this branch. -->

## Exact tested state

- Branch and PR base:
- Local HEAD and verified remote SHA (`tools/verify_remote_publication.py`):
- Stacked on another PR? (`--stack-parent-pr`; name it and its SHA):
- Dependencies and overlapping PRs:

## Summary

<!-- What changed and why? -->

## Scope

<!-- Main code, docs, tooling, or records touched. Keep this concise for small changes. -->

## Evidence classification

- [ ] Honda-confirmed evidence
- [ ] External prior art
- [ ] Synthetic test value
- [ ] Hypothesis / unknown retained explicitly

## What changed

<!-- Include relevant files and user-visible effects. -->

## Tests

<!-- Commands and results; note capability-based skips. -->

## Vehicle interaction

- [ ] NONE — offline only
- [ ] READ-ONLY
- [ ] REVERSIBLE TEST
- [ ] LIVE MUTATION

## Risk / rollback

<!-- For offline-only changes, state "None — offline only". For vehicle work, include failure behavior and rollback. -->

## Target writes

- [ ] NONE
- [ ] Proposed — describe only within a separately reviewed milestone

## Publication and public safety

- [ ] Published through `tools/publish_checkpoint.sh` with an explicit file list (no blanket staging, no force-push)
- [ ] `tools/check_public_safety.py` passed on this candidate; any allowlist change is explained below
- [ ] The exact head received the required checks (a stale run is not evidence)

## Independent review

- [ ] `@ECC` or another independent reviewer examined this exact head — name them; otherwise write **none** (a self-review or another AI agent's review is not an eligible approval)
- Review state:

## Privacy review

- [ ] No private captures, credentials, identifiers, or proprietary binaries added
- [ ] Sanitized logs only

## Unknowns and remaining blockers

<!-- What remains unproven? -->

## Documentation updated

- [ ] `docs/status/current.md` and `docs/status/milestones.json`, if status changed
- [ ] EVIDENCE_INDEX.md, if evidence changed
- [ ] NEXT_ACTION.md, if the concrete next task changed
- [ ] Step report, if this is a milestone
- [ ] Link and privacy checks passed; independent review names the exact scope
