# Pull request triage (CL-OPS-RECOVERY-01)

Live state on 2026-10-22: 17 open PRs. The classifications use these words: MERGE_CANDIDATE (checks pass, no known defect; still needs the normal review and owner-authorized protected-main merge), NEEDS_FIX, KEEP_DRAFT, SUPERSEDED, BLOCKED (waiting on independent review or a dependency), ARCHIVE_CANDIDATE. **No PR was closed, merged or rebased by this triage**, and `mergeable: UNKNOWN` is not treated as a conflict.

| PR | Draft | Base | Files | GitHub merge state | Checks | Owner | Class | Notes |
|---|---|---|---|---|---|---|---|---|
| #7 Historical R6D static Honda MFi oracle path and inert receiver contract | no | `main` | 6 | conflicting / dirty | success 7 | architecture/R6D (maintainer) | **SUPERSEDED** | The clean-history replacement merged as #50 (`codex/cl-gh-07-r6d-clean`). Conflicts with `main`; 7 historical commits; of its 6 files none is new on `main`. Close only with owner approval; keep the branch until the worktree is retired. |
| #19 R7E parked-car compatibility preparation (78 historical commits, 100 files) | no | `main` | 100 | conflicting / dirty | success 7 | architecture/R7E (maintainer) | **ARCHIVE_CANDIDATE** | Conflicts; 68 of 100 files do not exist on `main`. The public-safety gate flags 1 local-account path in 295 changed files. Historical branch with private-data risk: publish nothing from it; extract needed content only through reviewed, focused PRs. |
| #53 CL-R13-A REA/xcertplay reference library (docs) | no | `main` | 17 | conflicting / dirty | success 7 | docs (maintainer) | **NEEDS_FIX** | Docs only; gate passes. Conflicts only because it edits the shared CL-R0 scope file and status docs that `main` has moved past. Rebase, refresh the digest, then a MERGE_CANDIDATE. |
| #65 CL-HH-06 Display 1 data flow and toolchain (research docs) | no | `main` | 11 | conflicting / dirty | success 7 | research (maintainer) | **NEEDS_FIX** | Docs; gate passes. Conflicts on the CL-R0 scope file, `.gitignore`, README. Rebase after #83/#84 so `.gitignore` is settled. |
| #67 CL-HH-07 HondaHack architecture assessment (3 docs) | no | `main` | 3 | unknown / unknown | success 7 | research (maintainer) | **MERGE_CANDIDATE** | Docs only; gate passes. GitHub reports mergeability UNKNOWN, which is not a conflict; it needs a fresh computation. Honda-related research: owner review required. |
| #68 CL-IF-01 cloud readiness and contract gates (2 docs) | no | `main` | 2 | mergeable / behind | success 7 | docs (maintainer) | **MERGE_CANDIDATE** | Docs only; gate passes; mergeable, only behind `main`. Update the branch, re-run checks. |
| #69 CL-GH-06 status reconciliation after #66 (10 status docs) | no | `main` | 10 | conflicting / dirty | success 7 | status maintenance (Codex) | **NEEDS_FIX** | All 10 files differ from `main`, which has moved past it; conflicts in the shared status files. Regenerate from current `main` through the designated maintenance workflow rather than merging stale text. Its worktree holds unpublished tooling (see the worktree inventory). |
| #73 CL-SOURCE-RECOVERY ledger (1 doc) | no | `main` | 1 | mergeable / behind | success 7 | Codex | **MERGE_CANDIDATE** | Docs only; gate passes; mergeable, behind `main`. |
| #74 CL-R12 early-host-disconnect correction (activity + test) | no | `main` | 2 | mergeable / behind | success 8 | Codex | **NEEDS_FIX** | Small, CI green, behind `main`. Overlaps the performance activity with #75, #79, #82. Merge it first among the Android PRs, then rebase the others on it. |
| #75 CL-R12 reusable synthetic frame storage (draft) | yes | `main` | 3 | mergeable / behind | success 8 | Codex | **KEEP_DRAFT** | Draft; touches the performance activity and the R12 workflow. Needs the buffer-ownership review described in section 5 before it can leave draft. |
| #78 CL-AUTH-01 Type111 authentication readiness (13 files) | no | `main` | 13 | mergeable / clean | success 8 | Claude | **BLOCKED** | Clean, CI green. Receiver authentication and security: needs independent review; never auto-merge. |
| #79 CL-INT-02 combined Android API17 integration (draft) | yes | `main` | 4 | mergeable / unstable | failure 2, success 9 | Codex | **KEEP_DRAFT** | Draft with 2 failing checks; overlaps #74/#75/#82. Re-derive from the integrated Phase 1 candidate rather than merge as is. |
| #80 CL-HONDA-111-01 research and synthetic pane/child models | no | `main` | 15 | mergeable / clean | success 8 | Claude | **BLOCKED** | Clean, CI green, public-safety gate passes. Honda receiver and display research with synthetic models: independent review required; never auto-merge. |
| #81 CL-HONDA-111-01 simulated Navigation pane leases (API17) | no | `main` | 7 | mergeable / blocked | failure 2, success 7 | Codex | **NEEDS_FIX** | Blocked by 2 failing checks: build omits the new classes, stale CL-R0 digest, and a contract-test regression. All three are fixed in #82. Do not merge #81 alone. |
| #82 API17 build, CL-R0 digests, honest CL-R12 verdicts, FD and PaneLease instrumentation (integrated candidate; contains #81's commits) | no | `main` | 17 | mergeable | all 4 workflows success at `a0ed09f` | Claude | **NEEDS_INDEPENDENT_REVIEW** | Retargeted to `main` on purpose: it contains #81's commits as ancestors and is the integrated Phase 1 candidate, so #81 is superseded by it rather than merged first. Offline CI, CodeQL, API17 navigation and CL-R12 pass at the exact head; CL-R12 is environment-sensitive (see the handoff). Not merged. |
| #83 Public-safety gate in CI with audited baseline allowlist | no | `main` | 8 | mergeable / clean | success 8 | Claude | **MERGE_CANDIDATE** | Clean; all checks pass including the new gate. Touches CI and `.gitignore`: owner review recommended. |
| #84 Verified stacked publication; one authoritative agent contract | no | `claude/cl-ops-recovery-01-public-s` | 8 | mergeable / clean | none yet | Claude | **MERGE_CANDIDATE** | Stacked on #83 through the new `--stack-parent-pr` path. Merge after #83. |

## Dependency chains

- **Phase 1 Android chain:** #81 (PaneLease) is not mergeable alone; #82 carries its required build, digest and contract fixes and is stacked on it. #74, #75, #79 and #82 all edit `MessengerFramePerformanceActivity.java`; #75 and #82 also edit the CL-R12 workflow. Local trial merges (discarded; no branch changed): #82 with `main` merges cleanly; #82 with #74 merges cleanly; #82 with #75 conflicts in the CL-R12 workflow and the performance activity; #82 with #79 conflicts in the activity. #75's own contract test pins the literal `Arrays.fill(pixels, marker);`, which #82 deliberately replaces with a byte-identical native-assisted fill, so #75's frame-storage change is covered by #82 and #75 should be re-derived or closed by its owner, not force-merged. #82 carries an equivalent producer-contract test. Reconcile by behaviour and tests: #74 first (smallest, green), then #75 after its buffer-ownership review, then the #81+#82 candidate, with #79 re-derived last. No PR in this chain is merged automatically.
- **Workflow chain:** #83 (public-safety gate) then #84 (stacked publication and agent contract). #84 is stacked on #83.
- **Research chain:** #80 (Honda receiver/pane research and synthetic models) and #78 (authentication) are independent of the Android chain but need independent review before merge.
- **Docs-only PRs** #53, #65, #67, #68, #73 and the status PR #69 are independent of everything above except for the shared files below.

## The shared-file hotspot

`docs/status/cl-r0-review-scope.json` pins a SHA-256 for 45+ source files and is edited by every PR that touches one of them: 7 of the 17 open PRs (#7, #53, #65, #69, #82, #83, #84) edit it, and it is the main reason #53, #65 and #69 now conflict. A digest refresh is mechanical, so each such PR is forced to conflict-resolve a file it does not otherwise care about. Options (a decision for the maintainers, none taken here): compute the digests in CI instead of pinning them in a shared file; split the pins into one small file per area; or keep the file and merge in a fixed order, refreshing at each step. Until then, expect that file to conflict whenever PRs are merged out of order.

## Recommended order (proposal; every step needs the normal authorization)

1. #83, then #84 (workflow safety and the agent contract; every later PR benefits).
2. Docs-only PRs that are green and only behind: #73, #68, then #67 after a fresh mergeability check.
3. #74, then the reconciled Phase 1 candidate (#81 with #82), after Codex's independent reproduction.
4. #53 and #65 after rebasing onto the settled `.gitignore` and scope file.
5. #69 regenerated from the then-current `main`.
6. Review-gated: #78 and #80, only with an independent human review; never automatically.
7. Archive after owner confirmation: #7 (superseded by #50) and #19 (historical).

## PR descriptions and links

Three PR titles were multi-line (the publication helper used the whole commit message as the title); they were shortened and the original text moved into each body. The helper now writes a one-line title and puts the rest in the body, with a regression test. Linking to tracker issues uses `Refs #N` unless the issue's acceptance conditions are met; no issue was closed by this work.
