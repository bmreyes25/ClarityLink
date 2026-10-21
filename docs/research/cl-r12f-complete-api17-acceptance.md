# CL-R12-F2 API 17 Performance and Reliability Acceptance

Status: **PARTIAL — controlled short A/B completed; performance and reliability acceptance remain unmet**
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
