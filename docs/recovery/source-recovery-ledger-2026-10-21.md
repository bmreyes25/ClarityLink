# ClarityLink source recovery ledger — 2026-10-21

## Scope and acceptance

This audit starts from the fetched `origin/main` commit `115ca976891daf95fd665f72d360dae19cceb111` in a task-owned worktree. It compares local refs and worktrees, source-like untracked files, and unreachable commit objects against current main and the repository's GitHub branches and pull requests. A recovery candidate is accepted only if its current source is missing, its provenance is clear, it is public-safe, and its relevant checks can be run without vehicle access.

No Type111, Android API 17, receiver, renderer, or test source met those recovery criteria. No source was copied into this worktree. The audit did not modify any pre-existing worktree or private research/archive.

## Source already present on main

- The current Type111 lab, producer, teardown, and reliability source and tests are present in main. Related published work includes [PR #20](https://github.com/bmreyes25/ClarityLink/pull/20), [PR #23](https://github.com/bmreyes25/ClarityLink/pull/23), [PR #25](https://github.com/bmreyes25/ClarityLink/pull/25), [PR #28](https://github.com/bmreyes25/ClarityLink/pull/28), [PR #30](https://github.com/bmreyes25/ClarityLink/pull/30), [PR #32](https://github.com/bmreyes25/ClarityLink/pull/32), and [PR #37](https://github.com/bmreyes25/ClarityLink/pull/37).
- API 17 receiver and runtime source is present, including the experimental Messenger pipeline. Its publication history includes [PR #16](https://github.com/bmreyes25/ClarityLink/pull/16), [PR #36](https://github.com/bmreyes25/ClarityLink/pull/36), and [PR #52](https://github.com/bmreyes25/ClarityLink/pull/52).
- Receiver and renderer contracts and tests are present through [PR #4](https://github.com/bmreyes25/ClarityLink/pull/4), [PR #9](https://github.com/bmreyes25/ClarityLink/pull/9), [PR #15](https://github.com/bmreyes25/ClarityLink/pull/15), [PR #16](https://github.com/bmreyes25/ClarityLink/pull/16), [PR #40](https://github.com/bmreyes25/ClarityLink/pull/40), [PR #45](https://github.com/bmreyes25/ClarityLink/pull/45), [PR #46](https://github.com/bmreyes25/ClarityLink/pull/46), and [PR #50](https://github.com/bmreyes25/ClarityLink/pull/50).
- The safeguards requested for this recovery are already in main through [PR #70](https://github.com/bmreyes25/ClarityLink/pull/70) and [PR #71](https://github.com/bmreyes25/ClarityLink/pull/71). The task's pre-existing dirty checkout contains local copies of the safeguard source and tests; each source-like copy checked was byte-identical to the file in current main. Those files were left untouched and were not staged here.

## Source superseded by current main

- In the existing `claritylink-session-closeout` worktree, `android/cl-imp-03-app/java/org/claritylink/android/MessengerFramePerformanceActivity.java` has an uncommitted edit. It removes the optional per-stage profiling instrumentation from the current implementation. The same bytes are preserved in the existing CL-R12 handoff bundle. The candidate differs from the profiled implementation in current main and is not a missing source recovery; it was preserved in place and not published. The current profiled API 17 implementation is part of [PR #52](https://github.com/bmreyes25/ClarityLink/pull/52).
- `claritylink-api17-recovery/.github/workflows/cl-r12-api17-runtime-recovery.yml` is an untracked older workflow copy. Its differences from main remove the verified archived SDK fallback and the baseline/candidate A/B build and receipts. Current main contains the expanded workflow published with [PR #52](https://github.com/bmreyes25/ClarityLink/pull/52); the older copy was not restored.
- The dangling commit objects `4c91fc79b77626e942d7daa1d5d893966469bee6`, `aa1f5c70bbe0e79404242cfeeae8480fb604809e`, `26cf1e69867e34520d9dd2299b4acf2ca7200bdd`, and `7e268a89a95c0e47386b6593892510aeaebcfc59` contain earlier Type111/API 17 contract-test and teardown revisions. Their affected source areas are represented by later merged revisions, including [PR #25](https://github.com/bmreyes25/ClarityLink/pull/25), [PR #28](https://github.com/bmreyes25/ClarityLink/pull/28), [PR #30](https://github.com/bmreyes25/ClarityLink/pull/30), [PR #32](https://github.com/bmreyes25/ClarityLink/pull/32), and [PR #38](https://github.com/bmreyes25/ClarityLink/pull/38). They were not replayed over current main.

## Private or restricted material

- Untracked research and vehicle-evidence material remains in its existing local worktrees. Raw captures, derived evidence, and vehicle-specific research were not copied, staged, or published.
- The HondaHack-Claude research project and its private archive were not opened or modified.
- No Honda, vehicle, ADB, or live-iPhone operation was performed. Current main keeps `DisplayPolicy.WarningVisibilityPolicy.safeForHonda()` unconditionally `false`.

## Local-only source that remains outside this recovery

These source files remain in their original worktrees and were not merged into the recovery branch:

- `claritylink-session-closeout/android/cl-imp-03-app/java/org/claritylink/android/MessengerFramePerformanceActivity.java` — uncommitted profiling-removal variant described above; a byte-identical preservation copy remains under `clarity-analysis/research/handoff/new-chat/cl-r12-f-preservation-20261020/`.
- `claritylink-cl-gh-06-reconcile/tools/github_repo_doctor.py` and `claritylink-cl-gh-06-reconcile/tests/tools/test_github_repo_doctor.py` — local-only repository-maintenance source outside the requested Type111/API 17 recovery scope; not reviewed or published here.
- `claritylink-audit-pr19/tests/vehicle/test_test3_admission_runner_v2.py` — locally modified vehicle-test source. It remains unreviewed and unpublished; it was not executed.
- `claritylink-api17-recovery/.github/workflows/cl-r12-api17-runtime-recovery.yml` — historical workflow copy; superseded by the main version and left preserved in place.

The dirty original checkout also has local safeguard copies matching current main, plus preserved handoff and private-evidence inventory files. None were altered by this task. Older local branch histories and the 96 commit objects reachable only from local refs were inventoried as history, not counted as source recoveries. In addition, `git fsck` reported 13 unreachable commit objects; the four relevant older source revisions are listed above. Counts are not evidence that all source changes are present or missing.

## Verification and publication record

- Recovery source units: none selected; no source tests were run for this audit.
- Safety invariant checked in current main: `android/src/main/java/org/claritylink/android/DisplayPolicy.java` returns `false` from `safeForHonda()`.
- Current main's required `Offline CI` and `CodeQL` checks were successful for `115ca976891daf95fd665f72d360dae19cceb111` at audit time.
- This ledger is the only new file in the recovery change. It is published as a documentation audit so the recovery outcome and remaining local-only source have a GitHub record.
