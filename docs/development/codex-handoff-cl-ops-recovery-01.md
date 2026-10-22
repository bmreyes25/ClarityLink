# Codex handoff: CL-OPS-RECOVERY-01 and CL-HONDA-111-02

Author: Claude (implementation). Independent review: **not performed**. Nothing here is an approval, and no
human or ECC review has taken place. Self-review and other-AI review are not eligible human approval.

Scope limits that still hold: `safeForHonda()` stays `false`; both Honda gates stay NO-GO
(`RECEIVER_AUTHORIZED_SPEC_REQUIRED`, `DISPLAY_SUPPORTED_PATH_NOT_FOUND`); no vehicle, ADB against Honda
hardware, receiver patching, Xposed, injection, CAN or firmware work was done. Everything below is a
synthetic API17 emulator result and says nothing about the vehicle.

## 1. What to review

| Item | Branch | PR | Exact tested head | Base |
|---|---|---|---|---|
| Phase 1 integrated candidate | `claude/cl-honda-111-02-verification-recovery` | #82 | `a0ed09fd054792d69723b3702c21bdad9c3dc004` | `main` (contains #81's commits as ancestors) |
| Public-safety gate | `claude/cl-ops-recovery-01-public-safety` | #83 | `05bfe46` | `main` |
| Publication workflow and agent contract | `claude/cl-ops-recovery-02-publication` | #84 | `6a120f7` | stacked on #83 |
| Reconciliation docs (this file) | `claude/cl-ops-recovery-03-reconciliation` | #85 | see the PR | `main` |
| Presentation, CODEOWNERS | `claude/cl-ops-recovery-04-presentation` | #86 | `1125fb1` | `main` |

Pre-change baseline for the CL-R12 comparison: `b9fa1a0b4aae11f71b257c3b7729470c5a8dc792` (`main`).
Research and synthetic models for the Honda Navigation pane: PR #80 (independent of the Android chain).

## 2. Root causes found (PR #82)

1. **API17 build omitted new classes.** `PaneEvent`/`PaneLease` (from #81) and `SyntheticFrameFill` were not in the
   explicit source list in `tools/build_cl_imp_03_apks.sh`. A dependency-closure test now guards this.
2. **CL-R12 false PASS.** The runner printed its PASS marker while gates failed and short-circuited on the baseline.
   Verdicts are now separate (`CL_R12_API17_RUNTIME_SCENARIO`, `CL_R12_GATE_BASELINE/CANDIDATE/SOAK`,
   `CL_PANE_LEASE_INSTRUMENTATION`); exit 11/12/13 for failed gate, missing teardown evidence, failed instrumentation.
3. **Throughput.** Producer `frame_generation` p50 was about 26 ms, dominated by `Arrays.fill` (a Java loop on Dalvik).
   `SyntheticFrameFill` fills a 4096-byte seed then doubles with `System.arraycopy`; it is byte-identical to
   `Arrays.fill` (20,000 random cases and 256 full frames on a host JVM). The producer also reuses its frame
   buffer and the returned-frame buffer.
4. **`setRendererViewport` revoked the lease.** Accepted geometry now applies in place and never calls `revokeLease()`.
5. **FD +3 on the producer.** One converter `HandlerThread` Looper (pipe pair plus epoll fd) is released only when its
   MessageQueue is finalized. Settled counts return to baseline (pre-settle +3, post-settle 0 in 8 of 8 runs).
6. **Revocation storm.** 60 attach/revoke cycles took the process from 37 to a peak of 178 descriptors because each
   attached view created its own converter thread. The backend now owns one shared converter thread, created
   lazily and quit in `close()`; the peak is 40 and returns to 37.
7. **Hung CI run** (emulator wedged for over 50 minutes): every adb call is bounded (180 s, `am instrument` 600 s),
   an `ERR` trap writes `CL_R12_RUNNER_ABORTED`, and the `R12B_DESTROY` wait has a 20 s grace.
8. **A/B harness defects** found while measuring: the renderer baseline must receive the candidate's workload files
   (`SyntheticFrameFill.java`, and, as of `a0ed09f`, `MessengerFrameParcel.java`) or it cannot compile. Run
   `39865066603` failed at that build step, not on performance.

The CL-R12 gate `tools/check_cl_r12_perf_gate.py` and its thresholds are unchanged: offered 29-31 fps, delivered
at least 27 fps, p95 at most 50 ms, p99 at most 100 ms, drops at most 10%, producer/host FD delta at most +2.

## 3. Evidence (workflow run IDs)

| Run | What | Result |
|---|---|---|
| 39840065674 | workload A/B at the native-fill head | candidate about 28 fps, p95 36 ms, p99 45 ms, drops 6-8%, FD delta 0; 3 of 3 candidate runs and soak PASS; baseline FAIL in the same run |
| 39850908696, 39854243866 | renderer A/B, PaneLease renderer vs pre-#81 renderer | NOT_DISTINGUISHABLE on every metric; 6 per-run gates and soak PASS |
| 39862437324 | pull_request at `aafdaa3` | SUCCESS: all 7 gates PASS, 27.5-28.1 fps |
| 39862243764 | workflow_dispatch at `aafdaa3` | **FAILURE**: baseline FAIL on 1 of 3, candidate FAIL on 3 of 3 (22.3-25.5 fps, drops 15-25%) |
| 39865061220 | workload A/B, `411e707` vs `aafdaa3` activity | all 7 gates PASS; p50 21.3 to 19.6 ms and p95 26.4 to 25.0 ms (candidate better); fps equal at about 29.8 (fast host) |
| 39865066603 | pull_request at `411e707` | FAILURE at the A/B build step (harness defect, fixed in `a0ed09f`); no performance data |
| 39867353829 | pull_request at `a0ed09f` | SUCCESS: scenario, baseline, candidate and soak gates PASS; instrumentation `OK (7 tests)`; renderer A/B about 28.7 fps, p95 about 32 ms, p99 about 41 ms, drops about 4%, FD delta 0, 0 pixel mismatches, every metric NOT_DISTINGUISHABLE |

Other workflows at `a0ed09f` (runs 39867353752, 39867353779, 39867353883): Offline CI, CodeQL and CL-FACTORY-03
API17 navigation all succeeded. The local full suite at `aafdaa3` was 1557 passed, 29 skipped, 0 failed; it was
not rerun on `a0ed09f` by this handoff's author (see section 7).

### How to read the CL-R12 result

The absolute gate passes in most but not all executions on shared GitHub runners. Across the five full executions of
the fast-producer builds, four passed and one failed (`39862243764`), with identical product code in a passing
and a failing run. The margin over the 27 fps floor is thin (about 1 fps on a typical host) and host speed varies
12-30 fps. This is **environment-sensitive, not a stable PASS**. Do not rerun until green and call it proven. The
`ab-summary` comparison is informational and never decides the gate.

Remaining per-frame costs: `pixel_compare` p50 about 7.8 ms (the exact byte-identity oracle, deliberately left
alone), `return_read_copy` about 2.3 ms, `decoded_frame_create` about 2.0 ms.

## 4. Local commands

```
tools/run_tests.sh                       # full suite (use a venv with pytest)
python3 tools/check_public_safety.py --base origin/main
python3 tools/check_repo_health.py
python3 tools/verify_remote_publication.py   # after any publish
```

CL-R12 dispatch (needs the workflow on `main` to dispatch from a branch, otherwise use a pull_request run):
inputs `ab_mode` (`renderer` or `workload`) and `baseline_ref`; `CL_R12_AB_REPEATS` is 3.

## 5. Trial merges (local, discarded)

#82 with `main`: clean. With #74: clean. With #75: conflicts in the workflow and the performance activity. With
#79: conflicts in the activity. #75's contract test pins the literal `Arrays.fill(pixels, marker);`, which #82
replaces; #75's single-buffer reuse was reviewed as safe (one frame in flight, `inFlight` cleared only after the
comparison, stale replies rejected on generation and sequence). #74 is a sound one-line fix.

## 6. Classification

| Item | Status |
|---|---|
| Android API17 build, PaneLease lifecycle, FD lifecycle (instrumentation) | PASS at `a0ed09f` |
| CL-R12 absolute gate | PARTIAL: passes at the exact head, environment-sensitive with a thin margin |
| Renderer A/B (PaneLease vs pre-#81) | PASS: no measurable difference |
| Public-safety gate and publication tooling | PASS (tests); independent review pending |
| Independent review | NOT DONE |
| Honda integration | NO-GO, unchanged |

## 7. Blockers and open items

- Independent review of #82 by Codex or a human reviewer, including a reproduction of the CL-R12 runs.
- No durable CI check exists for the heads of stacked PRs (Offline CI and CodeQL trigger only for PRs based on
  `main`); the rule is documented in `AGENTS.md`, not enforced.
- Full `tools/run_tests.sh` at the final merged head, and DEX class inspection of the lab and pane-test APKs, are
  still to be run by the reviewer.
- Needs owner authorization and was **not** done: rewriting history to remove a local account name from 57 paths
  on `main` (428 across history); deleting the 18 merged branches that are eligible; retiring worktrees; enabling
  auto-delete of head branches; moving the CL-R12 absolute thresholds to a dedicated runner or splitting required
  checks.
