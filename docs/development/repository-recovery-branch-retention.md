# Branch retention report (dry run) — CL-OPS-RECOVERY-01

Dry-run inventory of the remote branches on 2026-10-22, built from live GitHub PR state. **Nothing was deleted, renamed or changed.** The earlier figure of 23 merged branches was a snapshot; the live count is below. A branch may be proposed for deletion only if all five conditions hold, and each is checked per branch.

| Condition | How it is checked here |
|---|---|
| Its useful changes are merged | The PR is `MERGED` and the branch tip equals that PR's final head, so no commit was pushed after the merge |
| No open PR depends on it | No open PR names it as its base |
| No agent or worktree owns it | No local worktree has it checked out |
| No unique unpublished work | Tip equals the merged PR head (above); local-only commits are reported separately in the worktree inventory |
| Deletion is authorized | **Not given.** This report is the proposal, not an action |

Remote branches other than `main`: **66** — merged **47**, with an open PR **17**, closed unmerged **1**, no PR **1**.

## Proposed for deletion once authorized (18)

Merged, tip equals the merged head, not a PR base, not checked out anywhere.

| Branch | Merged PR |
|---|---|
| `campaign/cl-ops-private-preservation` | #22 |
| `cl-overnight-05-compositor-owner-death` | #31 |
| `cl-overnight-06-reentrant-teardown` | #32 |
| `cl-r4-followup` | #38 |
| `cl-r4a-session-sink-reattach` | #23 |
| `cl-r4b-producer-recovery-prompt1` | #30 |
| `cl-r4b-reliability-closure-01` | #33 |
| `cl-r4b-security-closure-02` | #34 |
| `cl-r7-lab` | #36 |
| `codex/cl-gh-07-r6d-clean` | #50 |
| `feature/cl-hh-02-geometry` | #45 |
| `feature/cl-r10c-integration-architecture` | #49 |
| `feature/cl-r9-honda-boundaries` | #40 |
| `feature/cl-r9a-control-setup` | #41 |
| `feature/cl-r9b-type111-handoff` | #42 |
| `feature/cl-r9c-factory-cluster-boundary` | #43 |
| `feature/cl-r9d-hondahack-boundary` | #44 |
| `publish/claritylink-current` | #20 |

## Merged but not yet eligible (29)

Every one of these is blocked only by a local worktree that still has it checked out (or, where noted, another reason). Retire the worktree first (owner approval), then re-run this check.

| Branch | Merged PR | Blocker |
|---|---|---|
| `architecture/r6-custom-receiver` | #4 | checked out in a local worktree |
| `architecture/r6b-auth-substrate` | #5 | checked out in a local worktree |
| `architecture/r6c-honda-auth-substrate` | #6 | checked out in a local worktree |
| `architecture/r6d-static-auth-closure` | #8 | checked out in a local worktree |
| `architecture/r6e-custom-receiver-auth-transport` | #9 | checked out in a local worktree |
| `architecture/r6f-authority-integration` | #11 | checked out in a local worktree |
| `architecture/r6g-livi-authority-bringup` | #12 | checked out in a local worktree |
| `architecture/r6h-livi-adapter-completion` | #13 | checked out in a local worktree |
| `architecture/r6h1-hardware-authority-bringup` | #14 | checked out in a local worktree |
| `architecture/r7a-integrated-offline-dual-carplay` | #15 | checked out in a local worktree |
| `architecture/r7b-api17-armv7-native-build` | #16 | checked out in a local worktree |
| `architecture/r7c-honda-target-adapters` | #17 | checked out in a local worktree |
| `architecture/r7d-integrated-target-simulation` | #18 | checked out in a local worktree |
| `cl-r4-reliability-completion` | #37 | checked out in a local worktree |
| `cl-r4b-final-acceptance-03` | #35 | checked out in a local worktree |
| `claude/cl-factory-01-architecture` | #76 | checked out in a local worktree |
| `codex/activate-publication-safeguards` | #71 | checked out in a local worktree |
| `codex/cl-factory-03-api17-structured-navigation` | #77 | checked out in a local worktree |
| `docs/cl-gh-local-01-publication` | #70 | checked out in a local worktree |
| `docs/cl-master-01-type111-program` | #54 | checked out in a local worktree |
| `docs/cl-r4-merged-status` | #39 | checked out in a local worktree |
| `docs/cl-sys-01a-factory-android` | #66 | checked out in a local worktree |
| `docs/clean-main-test-receipt` | #21 | checked out in a local worktree |
| `docs/codex-workflow-autopublish` | #51 | checked out in a local worktree |
| `experiment/cl-r12f-api17-public-runtime` | #52 | checked out in a local worktree |
| `feature/cl-hh-03-view-observability` | #46 | checked out in a local worktree |
| `feature/cl-r10a-type111-receiver-handoff` | #47 | checked out in a local worktree |
| `feature/cl-r10b-display-ownership` | #48 | checked out in a local worktree |
| `research/r5d-artifact-provenance` | #3 | checked out in a local worktree |

## Not merged — keep

| Branch | PRs |
|---|---|
| `architecture/r6d-factory-mfi-oracle` | #7 open |
| `architecture/r7e-parked-car-compatibility-preparation` | #19 open |
| `claude/cl-auth-01-type111-readiness` | #78 open |
| `claude/cl-honda-111-01-factory-receiver` | #80 open |
| `claude/cl-honda-111-02-verification-recovery` | #82 open |
| `claude/cl-ops-recovery-01-public-safety` | #83 open |
| `claude/cl-ops-recovery-02-publication` | #84 open |
| `codex/cl-honda-111-01-api17-pane-lease` | #81 open |
| `codex/cl-int-02-android-api17-integration` | #79 open |
| `codex/cl-r12-f4-api17` | #75 open |
| `codex/cl-r12f-runtime-reliability` | #74 open |
| `codex/cl-source-recovery-ledger` | #73 open |
| `docs/cl-gh-06-status-reconciliation` | #69 open |
| `docs/cl-if-01-cloud-ready-contract-gates` | #68 open |
| `docs/cl-r13-a-rea-xcertplay` | #53 open |
| `research/cl-hh-06a-apk-inventory` | #65 open |
| `research/cl-hh-07-deep-architecture` | #67 open |
| `codex/final-desktop-hooks-test` | #72 closed |
| `experiment/r5z-custom-jmcs` | none |

## Settings

GitHub's "automatically delete head branches" is currently **off**. Turning it on is low-risk once the open stacked PRs (#81/#82, #83/#84) are integrated, because it deletes only the head branch of a merged PR and never an unmerged one; it must be enabled after the stacks are merged, because deleting a parent branch can retarget or close PRs still stacked on it. It does not change branch protection or auto-merge. It is a repository setting change and is left for the owner.

## Not done on purpose

- No branch was deleted, force-pushed or renamed.
- No local worktree was removed or pruned (see the worktree inventory).
- Squash-merged branches are judged by the PR's recorded final head, not by Git ancestry; a squash merge leaves the original commits outside `main`'s history, so `git branch --merged` would wrongly report them as unmerged.
