# CL-HONDA-111-02 — CI recovery, FD investigation and Codex test handoff

Offline and CI-only work. No Honda ADB, live iPhone, receiver patching, Xposed, CAN, cluster control, firmware change or vehicle test occurred. `safeForHonda() == false`. Both Honda admission gates remain **NO-GO**.

Branch `claude/cl-honda-111-02-verification-recovery`, stacked PR #82 (base: PR #81's branch `codex/cl-honda-111-01-api17-pane-lease`, starting reference `c90390ddfb6f285af5a2044f1332598c76048978`). The exact tested head is the PR head recorded in the PR description at hand-off.

## 1. Defects found and corrected

| # | Defect | Evidence | Fix |
|---|---|---|---|
| 1 | The API17 build omitted `PaneEvent.java` and `PaneLease.java`, which PR #81's `Display1OutputBackend` references. | Reproduced locally: removing the two lines gives `cannot find symbol` in `Display1OutputBackend.java`. | Added both to the **explicit** list in `tools/build_cl_imp_03_apks.sh`. New offline test `tests/tools/test_cl_imp_03_build_source_completeness.py` checks the renderer dependency closure (it fails on the original script) and that the list stays explicit with `-source 1.7 -target 1.7`. |
| 2 | Two pinned CL-R0 digests were stale (`Display1OutputBackend.java` after PR #81; the build script after fix 1), later two again after fix 5. | `tools/check_repo_health.py` and PR #81's Offline CI. | Updated exactly the changed pins in `docs/status/cl-r0-review-scope.json`, with a dated note. `approval_claimed` stays `false`, `review_status` and historical ranges are unchanged, and the note states it extends no review. |
| 3 | The CL-R12 runner printed `CL_R12_API17_RUNTIME_PASS` and the job passed while the baseline performance gate failed. | Run 39823597843: baseline gate FAIL on four checks, job `success`. | Scenario, each performance gate, teardown evidence and the PaneLease instrumentation test are now separate verdict lines in `final-status.txt`. A failed candidate gate exits 11, missing teardown evidence exits 12, a failed instrumentation test exits 13, and the PASS marker is reached only if none occurred. |
| 4 | The candidate gate was never evaluated when the baseline failed (`A && B` short circuit). | Run 39823597843 produced one gate file only. | Every run is gated independently with the unchanged `tools/check_cl_r12_perf_gate.py`. |
| 5 | `R12B_DESTROY` was declared "missing" at the first poll after a result because the 5-second rule counted from launch, not from the result. | Same run: all four short variants "missing"; with a 20-second grace from first sight of the result, teardown evidence is present in every run (destroy_evidence=present). | Grace period measured from the result. A true miss is still recorded and fails the job. |
| 6 | The A/B swapped only the performance Activity while both variants used the **same current renderer**, so it could not measure PR #81. | `.github/workflows/cl-r12-api17-runtime-recovery.yml` before this change. | `tools/build_cl_r12_renderer_ab.sh` builds the baseline from the last commit shared with `main` plus the candidate's identical workload Activity, in a separate detached worktree, signed with one shared keystore. It records baseline/candidate commits, renderer tree digests, build-script digests and APK hashes. |
| 7 | One baseline/candidate pair on the shared emulator is not evidence. | The same build gave 25.6 fps in one run, 14.9 in the next and 12.4 in a third. | `CL_R12_AB_REPEATS=3`: alternating A B / B A / A B pairs. `tools/summarize_cl_r12_ab.py` reports every run, medians, range overlap, and a 5% materiality floor. It never decides an acceptance gate. |
| 8 | `setRendererViewport` revoked the lease after PR #81, which broke the CL-R6 live-output contract and failed `tests/display/test_cl_imp_03_application_contract.py`. | Local full suite: 1 failed, 1545 passed on the PR #82 tree; PR #81's own Offline CI also failed. | The method carries phone-accepted ViewArea/SafeArea. The CL-HONDA-111-01 handoff wording conflated it with a host viewport change; a host viewport change arrives as a `PaneEvent` and still revokes. In-place application is restored (valid lease and View required, else `IllegalStateException`). The pinned contract test now asserts the synchronized signature and that the method never revokes. |
| 9 | `Display1PaneLeaseLifecycleTest` and `PaneLeaseTest` were referenced by no script, runner or workflow, and `PaneLease` binds to the main Looper so a host JVM cannot run them. | `git grep` found only self-references; `tools/test_r7c_java_api17.sh` lists neither. | `tools/build_cl_honda_111_pane_test_apk.sh` builds a permission-free synthetic instrumentation APK (`android/cl-honda-111-pane-test/AndroidManifest.xml`); the runner executes both PaneLease instrumentation classes with `am instrument` in the emulator session CI already boots. New `Display1RendererViewportInPlaceTest` covers fix 8. |

## 2. Producer file-descriptor finding

Baseline 46 to final 49 in every run measured the old way, both variants; host 32 to 32. Attribution from the new diagnostics: the descriptors added are one `pipe` pair and one `anon_inode:[eventpoll]`, which is exactly one native `Looper`. `ClarityLinkContentView.beginSession` lazily creates the `ClarityLinkFrameConvert` HandlerThread after the baseline sample; `close()` calls `quit()`, but on API 17 a quit thread's `MessageQueue` descriptors are released only when the queue is finalized.

| Statement | Class |
|---|---|
| The three descriptors are one lazily created native Looper: a `pipe` pair plus `anon_inode:[eventpoll]` | Observed (run 39825691081 per-descriptor diff) |
| They are held until finalization and released by collection: **before** a forced collection the delta is +3 in 8 of 8 runs; **after** it the delta is 0 in 8 of 8 runs, in the same build and the same runs | Observed (run 39829068486, `final_pre_settle` vs `final`) |
| The converter thread has already exited by the time of the count (it is absent from the thread list), so only its queue's descriptors remain | Observed (`R12B_THREADS`) |
| It is not per-frame growth: the count is constant over about 770 frames and memory-file counters balance (created = closed, open 0) | Observed |
| It also occurs in the pre-PR-#81 renderer | Observed (baseline variant) |
| Run 39826788951 showed 0 even before collection: a collection ran by chance in that run | Observed; GC timing is not deterministic, which is why the old, unsettled count passed or failed by luck |
| `producer_fd_returns_within_two` is `PASS` on every variant of the latest run, using the settled count | Observed (`perf-*-gate.txt`) |

Conclusion: a delayed-release effect of a quit helper thread, demonstrated before and after in one build; not an unbounded leak and not a PaneLease regression. The final count is now taken after a forced collection, the pre-collection count is logged beside it, and added descriptors and threads are named. **A descriptor that survives collection still fails the unchanged `+2` gate.** This corrects an observation taken before a required cleanup phase; no threshold was relaxed and nothing was hidden. The renderer was not changed for this.

## 3. CL-R12 results (every number is from a CI receipt)

Environment: GitHub `ubuntu-22.04`, 4 vCPU, `/dev/kvm` present and `emulator -accel-check` reports "KVM (version 12) is installed and usable"; Android 4.2.2 / API 17 / x86, `swiftshader_indirect` headless. The shared-runner throughput varied by host from about 12 to about 25 fps across runs of the same code.

| Run | Head | What it shows |
|---|---|---|
| 39823597843 | `f919c60` merge | Old method: baseline 14.6 fps, p95 67.2 ms; "candidate" (Activity swap) 15.2 fps, p95 57.6 ms; gate FAIL; job green; teardown "missing" |
| 39824606567 | `d683c7f` | Renderer-isolating pair: 24.6 vs 25.6 fps; p95 46.3 vs 46.5 ms; teardown present; job aborted by a runner bug (fixed) |
| 39825691081 | `ca26d30` | 20.0 vs 14.9 fps (shows why one pair is not evidence); per-descriptor FD attribution captured |
| 39826788951 | `7aa9b03` | Three alternating pairs, about 12.4 fps both; no metric distinguishable; FD delta 0 even before collection |
| 39829068486 | `4375d70` | Three alternating pairs, about 15.1 vs 15.0 fps, a 0.7% difference (labelled negligible); **PaneLease instrumentation `OK (2 tests)`**; FD delta +3 before and 0 after collection in 8 of 8; teardown present |

Across the repeated runs the PaneLease renderer shows no material throughput, latency, drop-rate or descriptor difference from the pre-PR-#81 renderer. **The unchanged gate still fails both variants** on delivered rate (needs 27 fps), valid-drop rate and, in some runs, p95; the soak is therefore not run. Classification: **environmental/workload capacity limit shared by both variants, not a PaneLease regression, and not resolved.** The profile run shows the dominant stage on the producer: synthetic `frame_generation` p50 about 26 ms per 800×480 frame, an allocation and fill of a new 1.5 MB array per frame under a 128 MB emulator heap. PR #75 (frame-storage reuse) targets that stage; it was not touched here to avoid overlapping Codex's work. **No representative performance PASS is claimed.**

## 4. Other verification

| Check | Result |
|---|---|
| API17 APK build (lab, disabled candidate, boundary attacker) | Passes locally and in CI; `PaneEvent`/`PaneLease` classes are in the dex input |
| Disabled candidate, no permissions, signing, fresh-directory policy | Unchanged; the pane-test APK also requests no permissions (checked by its builder) |
| `tests/tools`, `tests/display` | Pass |
| Full configured suite (`tools/run_tests.sh`) | Before fix 8: 1545 passed, 1 failed (defect 8), 29 skipped. Rerun on the final head is recorded in the PR |
| `tools/check_repo_health.py`, `tools/check_source_discovery.py` | Pass (0 ignored source) |
| Gitleaks | Clean on the changed files |
| CodeQL and Offline CI | Workflows trigger for PRs based on `main` only; see the PR for the run at the final head |
| `@ECC` | Not available. A self-review by the author is not independent review and no approval is claimed |

## 5. What stays open, with evidence

1. Representative CL-R12 performance gate: fails for both variants, environmental or workload-bound, unresolved. Owner: whoever owns the synthetic producer (PR #75) and the runner capacity decision.
2. A red CL-R12 job is now the honest result on shared runners. Whether to keep the job blocking, move the absolute thresholds to a dedicated runner, or make the job informational is a policy decision for the maintainers; the threshold script was not changed.
3. The `ClarityLinkFrameConvert` thread is created per attach and its descriptors persist until a collection finalizes its queue. With the settled measurement the unchanged gate passes, but a lifecycle storm of attach/revoke cycles (the PaneLease design) could hold several such queues at once until the next collection. A shared or pre-created converter thread would remove that; it is a renderer design change left to its owner and not measured here.
4. Overlap risk: `MessengerFramePerformanceActivity.java` (diagnostics, additive only) and `tools/run_cl_r12_api17_ci.sh`/the R12 workflow overlap files owned by PRs #74, #75 and #79 and will conflict on merge. Resolve in favour of keeping both sides.
5. Stacking consequence: Offline CI, CodeQL and CL-FACTORY-03 do not run for a PR whose base is not `main`.
6. `tools/publish_checkpoint.sh` refuses new branches that do not start at `origin/main`; this branch was created by a plain non-force push of PR #81's already-public head, after which the tool was used for every checkpoint.

## 6. Exact commands for Codex

```sh
git fetch origin && git checkout <PR #82 head SHA>        # detached; do not modify this branch
git diff --stat c90390ddfb6f285af5a2044f1332598c76048978..HEAD
python -m pytest -q tests/tools tests/display
python3 tools/check_repo_health.py && python3 tools/check_source_discovery.py
sh -c 'CL_IMP_03_BUILD_DIR=/tmp/cl-imp-03-qa-$$ tools/build_cl_imp_03_apks.sh'   # fresh dir; expect CL_IMP_03_APKS_BUILT
tools/build_cl_honda_111_pane_test_apk.sh /tmp/cl-pane-test-$$                   # expect CL_HONDA_111_PANE_TEST_APK_BUILT
tools/build_cl_r12_renderer_ab.sh "$(git merge-base HEAD origin/main)" /tmp/cl-r12-ab-$$   # needs a clean tracked tree
PATH=<venv>/bin:$PATH tools/run_tests.sh
gh run list --branch claude/cl-honda-111-02-verification-recovery
gh run download <CL-R12 run id> && python3 tools/summarize_cl_r12_ab.py <receipt dir>
```

Read in the receipt: `final-status.txt` (separate verdicts), `accel.txt`, `identity.txt`, `perf-*-gate.txt` (unchanged gate output per run), `perf-*-destroy.txt`, `R12B_FD_DIFF`/`R12B_THREADS` lines in `perf-*-logcat.txt`, `pane-lease-instrumentation.txt`, `ab-summary.md`, `source-ab.sha256`.

**Implementation verification here:** local build, tests, health, scans and the CI receipts above. **Needs Codex's independent reproduction:** the APK/dex contents, the instrumentation result, the CL-R12 receipts and metrics, the FD attribution, the full suite on the exact head, and whether in-place geometry (fix 8) is the intended contract for the lab flow.
