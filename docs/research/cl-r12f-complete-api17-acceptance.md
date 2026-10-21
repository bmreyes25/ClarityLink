# CL-R12-F2 API 17 Performance and Reliability Acceptance

Status: **in progress; API 17 execution is required before this report can be closed**
PR: [#52](https://github.com/bmreyes25/ClarityLink/pull/52)
Issue: [#58](https://github.com/bmreyes25/ClarityLink/issues/58)

## Scope and safety

This work uses only the synthetic ClarityLink Android lab on the GitHub-hosted Android 4.2.2/API 17/x86 emulator. It does not use Honda software, vehicle interfaces, Honda ADB, CAN, or a live iPhone. `safeForHonda() == false`.

## Source and runtime procedure

The API 17 workflow builds the baseline performance activity from the immediately preceding PR-head commit, then builds the optimized activity from the tested commit. All other source inputs, runner, emulator image, dimensions, frame cadence, preflight, and 30-second workload are held constant. Both APK hashes and runtime receipts are retained as workflow artifacts. The previous source is read from Git history; no existing worktree is rewritten.

The runtime runner first executes the established synthetic CL-R12 integration scenario. It then runs the baseline and optimized 30-second synthetic performance activity. The 10-minute optimized soak starts only if both short runs pass the fixed rate, latency, byte-integrity, queue, frame-accounting, memory-file, file-descriptor, heap, and final-stat checks. A skipped soak is reported as not run, not as a pass.

The performance activity measures offer, accepted, delivered, drops, p50/p95/p99/max elapsed latency through returned-byte validation and renderer submission, queue high-water, byte identity, process Java/native heap, file descriptors, and MemoryFile accounting. It does not establish compositor presentation or physical display scanout. The workflow does not take per-frame screenshots; screenshot overhead is zero for these runs. Process CPU, per-stage timing breakdowns, and emulator PSS are not currently measured and remain open acceptance items.

## Fault matrix

The existing API 17 scenario exercises a synthetic partial-frame rejection, stale-generation rejection, Navigation withdrawal, interrupt preemption, simulated host process death/recovery, and Type110-path isolation. The following requested cases are not covered by this receipt unless an explicit result is added below: ten teardown/reconnect cycles; invalid frame size; closed PFD; Messenger send failure; sender death; duplicate identity; out-of-order generation; stale producer after reconnect; rapid attach/detach; partial allocation/mapping failure; and cleanup after each individual injected failure. No claim of full failure-matrix acceptance is made from the smoke scenario or performance run.

## Results

Populate this section from the attached run artifacts only. Keep the baseline and optimized measurements distinct, retain all failures, and identify any skipped workload.

| Gate | Result |
| --- | --- |
| Build and API 17 runtime identity | Pending hosted run |
| Original synthetic CL-R12 scenario | Pending hosted run |
| Baseline 30-second performance | Pending hosted run |
| Optimized 30-second performance | Pending hosted run |
| Optimized 10-minute soak | Conditional; pending short-run gates |
| Full 15-case fault matrix | Not implemented |
| Per-stage and CPU instrumentation | Not implemented |
| Independent review | Not available through the connected review service; no approval claimed |

The acceptance remains **PARTIAL** unless all published correctness, performance, resource, and fault-matrix criteria are individually met. A successful emulator boot or synthetic smoke test alone does not complete CL-R12-F2.
