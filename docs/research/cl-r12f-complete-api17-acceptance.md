# CL-R12-F2 API 17 Performance and Reliability Acceptance

Status: **PARTIAL — CL-R12-F3 added stage measurements; performance and reliability acceptance remain unmet**
PR: [#52](https://github.com/bmreyes25/ClarityLink/pull/52)
Issue: [#58](https://github.com/bmreyes25/ClarityLink/issues/58)
Hosted runs: [paired A/B 1](https://github.com/bmreyes25/ClarityLink/actions/runs/39555976565), [paired A/B 2](https://github.com/bmreyes25/ClarityLink/actions/runs/39556434895), [paired A/B 3 at this report's head](https://github.com/bmreyes25/ClarityLink/actions/runs/39556881547)

## Scope and safety

This work uses only the synthetic ClarityLink Android lab on the GitHub-hosted Android 4.2.2/API 17/x86 emulator. It does not use Honda software, vehicle interfaces, Honda ADB, CAN, or a live iPhone. `safeForHonda() == false`.

## Source and runtime procedure

The API 17 workflow builds the baseline performance activity from the pinned pre-optimization PR source (`2d4c5f74…`) and the optimized activity (`73365283…`) from the tested commit. It verifies the source digests and refuses byte-identical APKs. Both APKs use one generated lab signing key, and each is installed fresh. Other source inputs, runner, emulator image, dimensions, frame cadence, preflight, and 30-second workload are held constant. APK hashes and runtime receipts are retained as workflow artifacts. The previous source is read from Git history; no existing worktree is rewritten.

The runtime runner first executes the established synthetic CL-R12 integration scenario. It then runs the baseline and optimized 30-second synthetic performance activity. The 10-minute optimized soak starts only if both short runs pass the fixed rate, latency, byte-integrity, queue, frame-accounting, memory-file, file-descriptor, heap, and final-stat checks. A skipped soak is reported as not run, not as a pass.

The performance activity measures offer, accepted, delivered, drops, p50/p95/p99/max elapsed latency through returned-byte validation and renderer submission, queue high-water, byte identity, process Java/native heap, file descriptors, and MemoryFile accounting. It does not establish compositor presentation or physical display scanout. The workflow does not take per-frame screenshots; screenshot overhead is zero for these runs. Process CPU, per-stage timing breakdowns, and emulator PSS are not currently measured and remain open acceptance items.

## Fault matrix

The existing API 17 scenario exercises a synthetic partial-frame rejection, stale-generation rejection, Navigation withdrawal, interrupt preemption, simulated host process death/recovery, and Type110-path isolation. The following requested cases are not covered by this receipt unless an explicit result is added below: ten teardown/reconnect cycles; invalid frame size; closed PFD; Messenger send failure; sender death; duplicate identity; out-of-order generation; stale producer after reconnect; rapid attach/detach; partial allocation/mapping failure; and cleanup after each individual injected failure. No claim of full failure-matrix acceptance is made from the smoke scenario or performance run.

## Results

Populate this section from the attached run artifacts only. Keep the baseline and optimized measurements distinct, retain all failures, and identify any skipped workload.

| Gate | Result |
| --- | --- |
| Build and API 17 runtime identity | PASS — Ubuntu 22.04 x86-64/KVM; Android 4.2.2/API 17/x86; emulator package 37.2.12; `swiftshader_indirect` |
| Original synthetic CL-R12 scenario | PASS — exact pixels, bounded queue, stale-generation rejection, Navigation withdrawal, interrupt preemption, synthetic host-process recovery, and Type110 isolation |
| Baseline 30-second performance | **FAIL gate** — three runs delivered 14.421, 14.218, and 14.609 FPS (mean 14.416); p95 69.55, 73.90, and 66.43 ms (mean 69.96); drops 51.9%, 52.6%, and 51.3%; queue high-water 1 |
| Optimized 30-second performance | **FAIL gate** — three runs delivered 15.307, 19.333, and 15.201 FPS (mean 16.614); p95 59.46, 52.94, and 59.01 ms (mean 57.14); drops 48.9%, 35.6%, and 49.3%; queue high-water 1 |
| Optimized 10-minute soak | **Not run** — both short runs failed one or more predeclared gates |
| Frame bytes and MemoryFiles | PASS for both short runs — no pixel mismatch, create/close counters balanced, open count zero in both processes |
| Heap and descriptors | Heap deltas stayed within 8 MiB. Producer descriptor count was 46→49 in both runs, exceeding the gate of +2; host stayed 32→32. This sample is before Activity destruction and does not establish post-destruction cleanup. |
| Full 15-case fault matrix | Not implemented |
| Per-stage and CPU instrumentation | Not implemented |
| Independent review | Not available through the connected review service; no approval claimed |

### Interpretation

Across three paired workflow runs, the optimized candidate averaged 2.20 more delivered frames/s than baseline (15.2%) and a 12.82 ms lower mean p95. The optimized result varied from 15.20 to 19.33 FPS and from 52.94 to 59.46 ms p95, showing material run-to-run variability. Both variants remain below the 27 FPS and 50 ms p95 gates, and drops remain above the 10% limit. These short samples do not support a stable performance claim. The optimization commit changes frame copying and reply processing/lifecycle handling together, so the result cannot isolate the contribution of copy removal. Stage timing and process CPU/PSS were not collected, so the bottleneck is not localized by these measurements.

An earlier run, [39555068735](https://github.com/bmreyes25/ClarityLink/actions/runs/39555068735), is excluded from A/B interpretation: both builds used the optimized source, and the baseline APK installation failed because the APKs had different signing certificates. The workflow now pins and verifies the actual baseline source digest and signs both builds with one lab key. The valid run's baseline and optimized APK SHA-256 values are recorded in its `apk-ab.sha256` artifact.

The acceptance remains **PARTIAL** unless all published correctness, performance, resource, and fault-matrix criteria are individually met. A successful emulator boot or synthetic smoke test alone does not complete CL-R12-F2.

## CL-R12-F3 stage-profile update

Source: [2550756](https://github.com/bmreyes25/ClarityLink/commit/255075605a0e33b5f99a0f842462e17e71be04c0). Exact-head API 17 workflow: [run 39610034532](https://github.com/bmreyes25/ClarityLink/actions/runs/39610034532). The run used the same 800×480, 30-second synthetic workload at 30 offered FPS, first for baseline and optimized candidates, then an optimized non-profile control and an optimized profile run. The pre-existing acceptance criteria are unchanged. No soak was run because the short gates failed.

| Variant | Delivered FPS | p50 latency | p95 latency | Dropped | Pixel mismatches |
| --- | ---: | ---: | ---: | ---: | ---: |
| Baseline | 14.409 | 52.19 ms | 69.74 ms | 51.9% | 0 |
| Optimized | 14.980 | 40.28 ms | 60.04 ms | 50.1% | 0 |
| Optimized profile control | 14.884 | 41.11 ms | 62.97 ms | 50.4% | 0 |
| Optimized profiled | 14.896 | 40.27 ms | 64.49 ms | 50.3% | 0 |

The prior runs and this new run consistently show substantial improvement relative to baseline but remain far below 27 FPS, above 50 ms p95, and above the 10% drop ceiling. The sequential profile/control sample differs by 0.012 FPS and 1.52 ms p95; this single pair does not establish instrumentation overhead reliably. The workload is application-level frame submission and pixel verification, not physical scanout. Screenshot capture was disabled, so its overhead was not measured.

The one profiled sample identifies multiple costly application stages rather than emulator compositor cost alone. Per-stage p50/p95 (447 samples except where noted):

| Stage | p50 | p95 |
| --- | ---: | ---: |
| Frame generation | 12.44 ms | 21.50 ms |
| Source MemoryFile write | 0.52 ms | 0.66 ms |
| Host read/copy | 2.62 ms | 4.72 ms |
| Host MemoryFile write | 0.45 ms | 0.60 ms |
| Host process through reply | 3.74 ms | 6.53 ms |
| Return read/copy | 2.66 ms | 4.16 ms |
| Pixel comparison | 13.81 ms | 23.01 ms |
| Decoded-frame construction | 2.75 ms | 3.32 ms |
| UI queue wait | 0.05 ms | 10.66 ms |
| Renderer attach | 0.013 ms | 0.016 ms |
| Renderer submit call | 0.016 ms | 0.039 ms |
| Offer through renderer submission | 40.26 ms | 64.47 ms |
| Bitmap creation (28 samples) | 4.01 ms | 5.52 ms |
| Pixel conversion and setPixels (28 samples) | 56.33 ms | 74.47 ms |
| Invalidate through draw (28 samples) | 4.84 ms | 12.35 ms |
| View draw (28 samples) | 0.039 ms | 0.084 ms |

Frame generation and full-frame pixel verification are the largest recurring producer-side costs. The profiled renderer conversion/setPixels path is also expensive on the sparse View-stage sample, but that sample count and instrumentation run do not establish it as the sole throughput limiter. Messenger dispatch, allocation, and descriptor preparation are smaller at p50; occasional high tails remain. Do not infer that changing transport alone will reach the FPS goal. No optimization was applied from this profile; a targeted change must be isolated and remeasured against correctness and resources.

### Resource and cleanup update

Across all four 30-second runs, producer descriptors were 46 before to 49 at final in-run sampling; the host stayed 32 to 32. MemoryFile create/close counts balanced in each process and open counts were zero. Producer native heap changed by only a few KiB, while Java heap rose by 4.3–10.4 MiB depending on run; the optimized run exceeded the existing 8 MiB bound. The new harness still did not observe its R12B_DESTROY marker within the grace period, so these data do not prove post-destruction descriptor cleanup or explain the +3. This remains a failed resource gate, not evidence that the descriptors are harmless or leaked.

The exact-head runtime smoke passed its existing scenario: synthetic pixel identity, stale-generation rejection, Navigation withdrawal, interrupt preemption, host-process recovery, and Type110-path isolation. This does not complete the requested fault matrix. Ten reconnect cycles and independent invalid-size, truncated-payload, closed-PFD, Messenger-failure, receiver/sender-death, duplicate-ID, out-of-order, stale-producer, rapid attach/detach, partial-allocation, and per-failure cleanup tests remain unverified. Factory-host simulation restoration remains represented only by the existing lab smoke behavior, not an independently accepted recovery proof.

The API 17 workflow itself passed on this head because its runtime smoke and receipt collection completed; performance acceptance did not. Offline CI and CodeQL are exact-head checks and must be read from PR #52. Keep the PR in draft and CL-R12-F **PARTIAL**. Next technical action: instrument heap/FD and destroy lifecycle at each connection boundary, then isolate profile-supported CPU work (generation and byte-for-byte comparison) in a controlled optimization, preserving the byte-integrity oracle and rerunning the API 17 A/B and failure matrix. Do not begin soak until every short-run gate passes.
