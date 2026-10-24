# Worktree inventory (CL-OPS-RECOVERY-01)

Read-only inventory of every local worktree of the maintainer's checkout, taken 2026-10-22 from Git's own worktree metadata. Paths are shortened and no file names from private areas are listed. **No worktree was deleted, pruned, moved or modified by this inventory.** Owners are inferred from the branch prefix (`claude/`, `codex/`), otherwise unattributed.

Total worktrees: **57**. Entirely clean with nothing unpublished: **48**. Everything else is classified below; none is unaccounted for.

| Worktree | Branch | PR | Tracked changes | Untracked | Unpublished commits | Class | Note / action |
|---|---|---|---|---|---|---|---|
| `7636/clarity-analysis` | `(detached)` | n/a | 0 | 0 | no upstream | DETACHED | Detached HEAD, clean; Codex scratch worktree. Owner decides. |
| `ClarityLab-r4-followup` | `docs/cl-r4-merged-status` | #39 merged | 0 | 0 | 0 | COMPLETED_MERGED | PR merged; clean; tip equals the merged head. Retire only with owner approval (see branch-retention report). |
| `ClarityLab/clarity-analysis` | `cl-r4-reliability-completion` | #37 merged | 3 | 8 | 0 | PRIVATE_RESEARCH_CHECKOUT | Stale branch (its PR is merged). The 3 modified and 5 of the untracked files are byte-identical to `main` (hooks, publication tools, their test). 9 unpublished private handoff notes name local paths. Large ignored raw evidence is present (firmware images, extracted trees, capture directories, build output; sizes recorded privately). Preserve; never publish; do not use as a workspace. **Action:** Keep. Verified private backup is a precondition to any relocation. |
| `cl-factory-03/clarity-analysis` | `codex/cl-factory-03-api17-structured-navigation` | #77 merged | 0 | 0 | 0 | COMPLETED_MERGED | PR merged; clean; tip equals the merged head. Retire only with owner approval (see branch-retention report). |
| `cl-honda-111-01-api17-pane-lease/clarity-analysis` | `codex/cl-honda-111-01-api17-pane-lease` | #81 open | 0 | 0 | 0 | ACTIVE | Owned by an open PR; clean and in sync. |
| `cl-r12-f4-api17/clarity-analysis` | `codex/cl-r12-f4-api17` | #75 open | 0 | 0 | 0 | ACTIVE | Owned by an open PR; clean and in sync. |
| `cl-r12f-runtime/clarity-analysis` | `codex/cl-r12f-runtime-reliability` | #74 open | 0 | 0 | 0 | ACTIVE | Owned by an open PR; clean and in sync. |
| `clarity-analysis-hooks-test` | `codex/final-desktop-hooks-test` | #72 closed | 0 | 0 | 0 | CLOSED_PR | PR closed unmerged; clean. Owner decides. |
| `clarity-int-02` | `codex/cl-int-02-android-api17-integration` | #79 open | 0 | 0 | 0 | ACTIVE | Owned by an open PR; clean and in sync. |
| `clarity-r5d` | `research/r5d-artifact-provenance` | #3 merged | 0 | 0 | 0 | COMPLETED_MERGED | PR merged; clean; tip equals the merged head. Retire only with owner approval (see branch-retention report). |
| `clarity-r5z-custom-jmcs` | `experiment/r5z-custom-jmcs` | none | 0 | 0 | 0 | NO_PR | No PR; clean. Owner decides. |
| `clarity-r6-custom-receiver` | `architecture/r6-custom-receiver` | #4 merged | 0 | 0 | 0 | COMPLETED_MERGED | PR merged; clean; tip equals the merged head. Retire only with owner approval (see branch-retention report). |
| `clarity-r6b-auth` | `architecture/r6b-auth-substrate` | #5 merged | 0 | 0 | 0 | COMPLETED_MERGED | PR merged; clean; tip equals the merged head. Retire only with owner approval (see branch-retention report). |
| `clarity-r6c-honda-auth` | `architecture/r6c-honda-auth-substrate` | #6 merged | 0 | 0 | 0 | COMPLETED_MERGED | PR merged; clean; tip equals the merged head. Retire only with owner approval (see branch-retention report). |
| `clarity-r6d-mfi` | `architecture/r6d-factory-mfi-oracle` | #7 open | 0 | 0 | 0 | ACTIVE | Owned by an open PR; clean and in sync. |
| `clarity-r6d-static-auth` | `architecture/r6d-static-auth-closure` | #8 merged | 0 | 0 | 0 | COMPLETED_MERGED | PR merged; clean; tip equals the merged head. Retire only with owner approval (see branch-retention report). |
| `clarity-r6e-auth-generation-validation` | `fix/r6e-auth-generation-validation` | none | 0 | 0 | 1 | UNPUBLISHED_COMMIT_UNVERIFIED | 1 local commit in no remote branch. Its `authentication.py` is identical to `main`; its test file differs. **Action:** Owner review: not verified as superseded. |
| `clarity-r6e-auth-transport` | `architecture/r6e-custom-receiver-auth-transport` | #9 merged | 0 | 0 | 0 | COMPLETED_MERGED | PR merged; clean; tip equals the merged head. Retire only with owner approval (see branch-retention report). |
| `clarity-r6f-authority` | `architecture/r6f-authority-integration` | #11 merged | 0 | 0 | 0 | COMPLETED_MERGED | PR merged; clean; tip equals the merged head. Retire only with owner approval (see branch-retention report). |
| `clarity-r6g-livi` | `architecture/r6g-livi-authority-bringup` | #12 merged | 0 | 0 | 0 | COMPLETED_MERGED | PR merged; clean; tip equals the merged head. Retire only with owner approval (see branch-retention report). |
| `clarity-r6h-livi-adapter` | `architecture/r6h-livi-adapter-completion` | #13 merged | 0 | 0 | 0 | COMPLETED_MERGED | PR merged; clean; tip equals the merged head. Retire only with owner approval (see branch-retention report). |
| `clarity-r6h1-hardware` | `architecture/r6h1-hardware-authority-bringup` | #14 merged | 0 | 0 | 0 | COMPLETED_MERGED | PR merged; clean; tip equals the merged head. Retire only with owner approval (see branch-retention report). |
| `clarity-r7a-integrated-offline-dual-carplay` | `architecture/r7a-integrated-offline-dual-carplay` | #15 merged | 0 | 0 | 0 | COMPLETED_MERGED | PR merged; clean; tip equals the merged head. Retire only with owner approval (see branch-retention report). |
| `clarity-r7b-api17-armv7` | `architecture/r7b-api17-armv7-native-build` | #16 merged | 0 | 0 | 0 | COMPLETED_MERGED | PR merged; clean; tip equals the merged head. Retire only with owner approval (see branch-retention report). |
| `clarity-r7c-honda-adapters` | `architecture/r7c-honda-target-adapters` | #17 merged | 0 | 0 | 0 | COMPLETED_MERGED | PR merged; clean; tip equals the merged head. Retire only with owner approval (see branch-retention report). |
| `clarity-r7d-target-simulation` | `architecture/r7d-integrated-target-simulation` | #18 merged | 0 | 0 | 3 | UNPUBLISHED_COMMITS_ON_MAIN | 3 local commits; `git cherry origin/main` reports each patch as already applied on `main`. **Action:** Safe to retire after owner approval; ref retained meanwhile. |
| `clarity-r7e-parked-car-preparation` | `architecture/r7e-parked-car-compatibility-preparation` | #19 open | 0 | 0 | 0 | ACTIVE | Owned by an open PR; clean and in sync. |
| `clarity-recovery/clarity-analysis` | `codex/cl-source-recovery-ledger` | #73 open | 0 | 0 | 0 | ACTIVE | Owned by an open PR; clean and in sync. |
| `claritylink-api17-public-candidate` | `experiment/cl-r12f-api17-public-runtime` | #52 merged | 0 | 0 | 0 | COMPLETED_MERGED | PR merged; clean; tip equals the merged head. Retire only with owner approval (see branch-retention report). |
| `claritylink-api17-recovery` | `experiment/cl-r12f-api17-runtime-recovery` | none | 0 | 1 | no upstream | SUPERSEDED_LOCAL | 1 untracked draft of a CL-R12 workflow; no upstream. `main` has an evolved workflow. **Action:** Keep ref; retire only with owner approval. |
| `claritylink-audit-pr19` | `overnight/cl-race-binder-view` | none | 1 | 606 | no upstream | PRIVATE_EVIDENCE | 606 untracked files (screenshots, text logs, checksum and JSON files) under the vehicle research tree, 1 modified test; no upstream. Unpublished by design. **Action:** Keep private. Owner decision required; do not publish. |
| `claritylink-cl-auth-01` | `claude/cl-auth-01-type111-readiness` | #78 open | 0 | 0 | 0 | ACTIVE | Owned by an open PR; clean and in sync. |
| `claritylink-cl-factory-01` | `claude/cl-factory-01-architecture` | #76 merged | 0 | 0 | 0 | COMPLETED_MERGED | PR merged; clean; tip equals the merged head. Retire only with owner approval (see branch-retention report). |
| `claritylink-cl-gh-06-68-refresh` | `docs/cl-if-01-cloud-ready-contract-gates` | #68 open | 0 | 0 | 0 | ACTIVE | Owned by an open PR; clean and in sync. |
| `claritylink-cl-gh-06-reconcile` | `docs/cl-gh-06-status-reconciliation` | #69 open | 2 | 2 | 0 | OWNED_UNPUBLISHED | PR #69's branch with 2 modified files and an unpublished repository-doctor tool and test (Codex CL-GH-06). PR #69 is stale against `main`. **Action:** Owner to publish through a focused PR or retire. |
| `claritylink-cl-gh-local-01` | `docs/cl-gh-local-01-publication` | #70 merged | 0 | 0 | 0 | COMPLETED_MERGED | PR merged; clean; tip equals the merged head. Retire only with owner approval (see branch-retention report). |
| `claritylink-cl-hh-06a` | `research/cl-hh-06a-apk-inventory` | #65 open | 0 | 0 | 0 | ACTIVE | Owned by an open PR; clean and in sync. |
| `claritylink-cl-hh-07` | `research/cl-hh-07-deep-architecture` | #67 open | 0 | 0 | 0 | ACTIVE | Owned by an open PR; clean and in sync. |
| `claritylink-cl-honda-111-01` | `claude/cl-honda-111-01-factory-receiver` | #80 open | 0 | 0 | 0 | ACTIVE | Owned by an open PR; clean and in sync. |
| `claritylink-cl-honda-111-02` | `claude/cl-honda-111-02-verification-recovery` | #82 open | 0 | 0 | 0 | ACTIVE | Owned by an open PR; clean and in sync. |
| `claritylink-cl-master-01` | `docs/cl-master-01-type111-program` | #54 merged | 0 | 0 | 0 | COMPLETED_MERGED | PR merged; clean; tip equals the merged head. Retire only with owner approval (see branch-retention report). |
| `claritylink-cl-ops-recovery-01` | `claude/cl-ops-recovery-01-public-safety` | #83 open | 5 | 0 | 0 | NEEDS_REVIEW | Has local changes not covered by a rule here. |
| `claritylink-cl-ops-recovery-02` | `claude/cl-ops-recovery-02-publication` | #84 open | 0 | 0 | 0 | ACTIVE | Owned by an open PR; clean and in sync. |
| `claritylink-cl-ops-recovery-03` | `claude/cl-ops-recovery-03-reconciliation` | none | 0 | 0 | 0 | NO_PR | No PR; clean. Owner decides. |
| `claritylink-cl-r0-publication` | `docs/cl-r0-closeout` | none | 0 | 0 | no upstream | NO_UPSTREAM | No upstream configured; clean. **Action:** Owner to confirm it is merged work, then retire. |
| `claritylink-cl-r10a` | `feature/cl-r10a-type111-receiver-handoff` | #47 merged | 0 | 0 | 0 | COMPLETED_MERGED | PR merged; clean; tip equals the merged head. Retire only with owner approval (see branch-retention report). |
| `claritylink-cl-r10b` | `feature/cl-r10b-display-ownership` | #48 merged | 0 | 0 | 0 | COMPLETED_MERGED | PR merged; clean; tip equals the merged head. Retire only with owner approval (see branch-retention report). |
| `claritylink-cl-r10c` | `feature/cl-r11-a-evidence-acquisition` | none | 0 | 0 | no upstream | NO_UPSTREAM | No upstream configured; clean. **Action:** Owner to confirm, then retire. |
| `claritylink-cl-r13-a` | `docs/cl-r13-a-rea-xcertplay` | #53 open | 0 | 0 | 0 | ACTIVE | Owned by an open PR; clean and in sync. |
| `claritylink-cl-r9` | `feature/cl-hh-03-view-observability` | #46 merged | 0 | 0 | 0 | COMPLETED_MERGED | PR merged; clean; tip equals the merged head. Retire only with owner approval (see branch-retention report). |
| `claritylink-cl-sys-01a` | `docs/cl-sys-01a-factory-android` | #66 merged | 0 | 0 | 0 | COMPLETED_MERGED | PR merged; clean; tip equals the merged head. Retire only with owner approval (see branch-retention report). |
| `claritylink-codex-workflow` | `docs/codex-workflow-autopublish` | #51 merged | 0 | 0 | 0 | COMPLETED_MERGED | PR merged; clean; tip equals the merged head. Retire only with owner approval (see branch-retention report). |
| `claritylink-hh-05a-readonly-proposal` | `experiment/cl-hh-05a-readonly-proposal` | none | 0 | 1 | 0 | UNREVIEWED_PROPOSAL | 1 untracked proposal for a live display observation. Not reviewed and not authorized for execution. **Action:** Keep; any use needs the vehicle-observation gate. |
| `claritylink-overnight05` | `cl-r4b-final-acceptance-03` | #35 merged | 0 | 0 | 0 | COMPLETED_MERGED | PR merged; clean; tip equals the merged head. Retire only with owner approval (see branch-retention report). |
| `claritylink-publication-candidate` | `docs/clean-main-test-receipt` | #21 merged | 0 | 0 | 0 | COMPLETED_MERGED | PR merged; clean; tip equals the merged head. Retire only with owner approval (see branch-retention report). |
| `claritylink-publication-safeguards-activation` | `codex/activate-publication-safeguards` | #71 merged | 0 | 0 | 0 | COMPLETED_MERGED | PR merged; clean; tip equals the merged head. Retire only with owner approval (see branch-retention report). |
| `claritylink-session-closeout` | `feature/cl-r12-hondahack-offline-lab` | none | 1 | 0 | 4 | UNPUBLISHED_COMMITS_SUPERSEDED | 4 local commits (CL-R12 offline Messenger lab, 2026-10-20) that exist in no remote branch, plus 1 modified file. The files they add exist on `main` in an evolved form (PR #52), but the commits themselves are not patch-equivalent. **Action:** Keep the branch ref (it is the only copy). Owner decides whether to archive as a tag. |

## What this does and does not establish

- Every dirty or unpublished worktree is named, classified and given an action. Nothing was published to clear a status: private evidence stays private, and owned unpublished work stays with its owner.
- "Clean" means Git reports no changes. It says nothing about ignored files, which are not protected by being ignored; the research checkout holds large ignored raw evidence that has no verified backup recorded here.
- A merged-and-clean worktree is only a retirement candidate. Removing one is destructive and needs owner approval after a verified recovery copy exists where relevant.
