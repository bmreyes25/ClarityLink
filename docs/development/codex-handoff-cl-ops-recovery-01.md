# Codex handoff: CL-OPS-RECOVERY-01 and CL-RECOVERY-FINAL

Author: Claude (implementation). Independent review: **not performed**. Nothing here is an approval, and no
human or ECC review has taken place; `@ECC` is not callable in this environment. Self-review and other-AI
review are not eligible human approval.

Scope limits that still hold: `safeForHonda()` stays `false`; both Honda gates stay NO-GO
(`RECEIVER_AUTHORIZED_SPEC_REQUIRED`, `DISPLAY_SUPPORTED_PATH_NOT_FOUND`); no vehicle, ADB against Honda
hardware, receiver patching, Xposed, injection, CAN or firmware work was done. Everything below is a
synthetic API17 emulator result and says nothing about the vehicle.

## 1. What to review

| Item | Branch | PR | Exact head | Base |
|---|---|---|---|---|
| Phase 1 integrated candidate | `claude/cl-honda-111-02-verification-recovery` | #82 | `404871a2e0a48d20aecf18d865618418acda5e9a` | `main` (contains #81's commits as ancestors; supersedes #81) |
| Public-safety gate | `claude/cl-ops-recovery-01-public-safety` | #83 | `33497f21714dce15a59f98c63f5a41b0285b6cfd` | `main` |
| Publication workflow and agent contract | `claude/cl-ops-recovery-02-publication` | #84 | `42c2c6e9b7b9798f24ad8f52f4d8cf09c0264211` | stacked on #83 (its older head `05bfe46`) |
| Reconciliation docs (this file) | `claude/cl-ops-recovery-03-reconciliation` | #85 | see the PR | `main` |
| Presentation, CODEOWNERS | `claude/cl-ops-recovery-04-presentation` | #86 | `d3b1efc78123086b4e4f51f461c88cc5181b745b` | `main` |

Pre-change baseline for the CL-R12 comparison: `b9fa1a0b4aae11f71b257c3b7729470c5a8dc792` (`main`).

## 2. PR #83: the allowlist bypass is fixed (defect found by the previous QA)

The old scanner read the candidate's own allowlist and only printed a notice when it was edited, so a PR could add
its own exemptions and pass (and a test asserted that). Now:

- The allowance comes from a **trusted ref** (the protected base), never from the candidate. The candidate's allowlist
  can only shrink: a new entry, a broader path, a higher count or a new sample exclusion fails (**PS009**).
- Modifying or deleting the scanner or `public-safety.yml` fails (**PS008**); such a change needs owner approval.
- Gitlinks, symlinks pointing outside the repository and unsupported modes fail (**PS010**).
- An unresolvable trusted ref, an invalid or unreadable allowlist, or any Git read failure is an error (exit 2), never a
  pass. A candidate with no allowlist file of its own (a branch cut earlier) simply gets only the trusted exemptions.
- The allowlist file itself is scanned (a secret in an entry's reason is found).
- `.github/workflows/public-safety.yml` is a `pull_request_target` workflow that checks out only the **base commit**,
  fetches the PR head as Git objects, and runs the base's scanner over them. It never checks out, installs or
  executes candidate code; read-only permissions; no secrets; event values reach the shell only through env vars.
  The `ci.yml` step is labelled supplementary because it runs the candidate's own scanner.
- 58 tests in `tests/tools/test_public_safety.py` build every unsafe fixture at run time in temporary repositories.
  When checked, sixteen of the new negative tests failed against the previous scanner (`05bfe46`) and pass now.
  Full suite on the worktree before the last small change: 1582 passed, 29 skipped.
- CI at `33497f2`: Offline CI, CodeQL and CL-FACTORY-03 succeeded.

**Limit, stated plainly:** `pull_request_target` workflows run from the default branch, so the protected check applies
only once #83 is merged through a reviewed bootstrap. Until then it is **not** enforced and the `ci.yml` result is
untrusted evidence. The check also only blocks merging if the owner makes it a required check or ruleset rule; this
work did not change repository settings. After merge, any PR that touches the scanner will report PS008 by design.

## 3. PR #84: stacked CI

#84 targets #83's branch, and Offline CI and CodeQL trigger only for PRs based on `main`, so GitHub has recorded **zero
checks** on #84's head. This is not resolved and not faked: the plan is that #83 is reviewed and merged, then #84 is
retargeted to `main` (no history rewrite; #83's commits are ancestors, so the diff shrinks to #84's own) and CI runs on
it. Supplementary only, not CI acceptance: a local trial merge of `d013daf` (then #83's head) into #84 was clean and the
full suite passed (`All configured offline checks passed`). `AGENTS.md` now describes the protected-baseline check.
Status: **externally blocked** on an eligible review and merge of #83.

## 4. PR #82: Phase 1 evidence at the exact head `404871a`

| Check | Result |
|---|---|
| Offline CI (run 39877125579), CodeQL (39877125838), CL-FACTORY-03 (39877125646) | success |
| Full local suite (`tools/run_tests.sh`) on the worktree before the `57ebeea` publish | all configured offline checks passed; the two later commits changed one instrumentation test, its contract test and a report, and ran the contract tests (16 passed) |
| CL-R12 (run 39877125636) | **failure**: scenario PASS, instrumentation `OK (7 tests)`, DEX verification PASS (x3), but the absolute gate failed (see below) |

**DEX verification** (the CL-R12 workflow runs the SDK `dexdump` on the built APKs and uploads a text report; no APK is
uploaded). Run 39877125636, `dex-verification.txt`: lab APK `4906978475b0...c45d1` (241 classes, `classes.dex`
`f2b7f6bd...4dea`) has `PaneEvent`, `PaneLease`, `Display1OutputBackend`, `ClarityLinkContentView`, `SyntheticFrameFill`,
`MessengerFramePerformanceActivity`, `MessengerFrameParcel` and the methods `SyntheticFrameFill#fill`,
`MessengerFrameParcel#read`, `Display1OutputBackend#setRendererViewport`, `ClarityLinkContentView#useSharedConverter`;
pane-test APK `8ec72fba...5f70` (133 classes) has the lease classes and all four instrumentation test classes plus
`PaneLeaseTest`; the renderer-mode baseline APK `3fb02d59...7720` has `SyntheticFrameFill` and the activity and, as
required, **does not** contain `PaneLease` or `PaneEvent`. The candidate `classes.dex` digest is identical in the
`57ebeea` and `404871a` runs (only a test changed between them). These are CI-built artifacts of the tested merge
commit recorded in the same file; they were not rebuilt locally (no SDK on the author's machine).

**Converter thread and descriptors.** Run 39877125636 logged `PANE_FD_CYCLES cycles=60 base=37 peak=40 before_settle=40
after_settle=37` and `PANE_CONVERTER_REUSE cycles=60 max_converter_threads=1`; the test asserts exactly one live
converter thread in every cycle, the same thread across all 60, and none after `close()`. The earlier pre-fix peak of 178
(base 37 + 141) is a historical measurement from before the shared converter. Callback fencing and stale-frame
rejection are asserted by the existing `Display1PaneLeaseLifecycleTest`. **A defect in my own first version of the new
check** (it retained the converter `Thread`, keeping its quit Looper's queue reachable) failed run 39873809281 with
`after_settle=40`; the product code was unchanged, the test was corrected to keep thread ids only, and the next run
returned to 37. The renderer was not modified in this round.

**CL-R12 absolute performance: PARTIAL, environment-sensitive.** The gate script and thresholds are unchanged. Valid full
executions of the fast-producer builds so far (performance verdict only): 39850908696 pass, 39854243866 pass,
39862437324 pass, 39862243764 **fail**, 39865061220 pass, 39867353829 pass, 39873809281 pass (its job failed on the test
defect above, not on performance), 39877125636 **fail**: **six pass, two fail**, on identical product code from
`b31d766` onward, with host speed varying from about 12 to about 30 fps. In the failing run the first pair passed in
both arms and the third pair degraded in **both** arms (candidate 22.6 fps with 223 drops; baseline 23.4 fps with 197
drops), which points at the host, not the renderer: the PaneLease renderer and the pre-#81 renderer remain
NOT_DISTINGUISHABLE on every metric. No run was repeated to obtain a green one, and the informational A/B does not
substitute for the gate. Classification: `CL_R12_FUNCTIONAL_PASS`, `CL_R12_ABSOLUTE_PERFORMANCE_PARTIAL`. What would
close it is a documented representative (or dedicated) runner for the absolute thresholds, or splitting the check; that is
an owner decision. Remaining per-frame costs: `pixel_compare` about 7.8 ms (the exact oracle, kept), `return_read_copy`
about 2.3 ms, `decoded_frame_create` about 2.0 ms. A 600 s soak at `a0ed09f` passed with 29.15 fps delivered, p95 31.4 ms,
p99 37.8 ms, 2.85% backpressure drops, 0 pixel mismatches and producer FDs 46 to 46 (run 39867353829).

## 5. Integration facts

- **#82 supersedes #81.** #82 contains #81's commits; close #81 as superseded only after #82 is accepted through the
  required process.
- **Trial merges (discarded; no branch changed).** #82 with `main`: clean. With #74: clean. With #75: conflicts in the
  CL-R12 workflow and the performance activity. With #79: conflicts in the activity. All five recovery heads merged in
  order (#83, #84, #82, #85, #86) conflict **only** in the trailing note keys of `docs/status/cl-r0-review-scope.json`
  (pure union of note keys; the union resolution passed repo health). #86's note was moved to an uncontended slot and
  now merges clean; #82's note is still at the tail and should be resolved by that union at integration, because
  touching #82 again would change its CI-tested head. `approval_claimed` stays `false` and no review range changed.
- **#75** pins the literal `Arrays.fill(pixels, marker);` in its own contract test, which #82 deliberately replaces
  with a byte-identical native-assisted fill; #82 carries an equivalent producer-contract test, so #75 should be
  re-derived by its owner on top of #82. Its single-buffer reuse was reviewed as safe (one frame in flight; `inFlight`
  cleared after the comparison; stale replies rejected on generation and sequence). **#74** is a sound one-line fix.
  Nothing in #74/#75/#79 was overwritten.
- **Compatibility with the new gate.** The corrected scanner run over the heads of #82, #85 and #86 against `main` with
  #83's allowlist as the trusted baseline passes. #84 shows PS008 only because, measured against `main`, it still carries
  #83's scanner commits; that disappears when #83 is merged and #84 retargeted.
- **CODEOWNERS (#86)** now also names `/tools/check_public_safety.py` and `/CLAUDE.md`, still only `@bmreyes25`; the
  ownership test allows exactly those two paths to be absent until #83 and #84 land. Required code-owner review is
  not enabled and no fictitious reviewer exists.

## 6. Classification

| Item | Status |
|---|---|
| `PUBLIC_SAFETY_GATE` | Fixed and tested at `33497f2` (CI green); **not enforced until #83 is merged**; independent review pending |
| `PUBLICATION_WORKFLOW` | PASS in tests (#84); **no CI recorded on #84's head** |
| `PHASE1_FUNCTIONAL` | PASS at `404871a`: scenario, instrumentation (7 tests), DEX verification, Offline CI, CodeQL, CL-FACTORY-03 |
| `CL_R12_PERFORMANCE` | PARTIAL: the CL-R12 check is red at `404871a` on the absolute gate (host variance); unchanged gate |
| `STACKED_CI` | BLOCKED: needs #83 reviewed and merged, then #84 retargeted |
| `INDEPENDENT_REVIEW` | NOT DONE |
| `MERGE_READINESS` | `READY_FOR_OWNER_REVIEW` for #83, #85, #86 (green checks); #82 reviewable but its CL-R12 check is red; #84 not ready (no CI) |
| `HONDA_INTEGRATION` | NO-GO, unchanged |

## 7. Approvals and decisions still needed from the owner

1. An eligible review (not the author, not an AI) of #83, then its merge; make `Public-safety gate (protected baseline)`
   a required check only if wanted.
2. After that, retarget #84 to `main` and let its CI run; then review and merge #84.
3. Review #82 including a reproduction of the CL-R12 runs; decide the policy for the absolute thresholds (dedicated or
   representative runner, or non-blocking absolute gate with the functional checks required).
4. Merge order proposal: #83, #84, #85, #86, then #82 (resolve the scope-file note union), then decide #74/#75/#79.
5. Not done, need explicit authorization: history rewrite to remove a local account name (57 paths on `main`, 428 across
   history), deleting the 18 eligible merged branches, retiring worktrees, auto-delete of head branches.
