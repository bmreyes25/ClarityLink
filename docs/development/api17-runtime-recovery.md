# CL-R12-F — API17 runtime and performance recovery

## Objective and baseline

Restore a repeatable Android 4.2.2 / API 17 runtime for the complete offline Navigation-host scenario, then measure the pipeline before making optimization claims. The CL-MASTER-01 request supplied historical figures of 30-second delivered FPS 1.12, 10-minute delivered FPS 1.41, offered rate approximately 30 FPS, drops about 95–96%, queue high-water 1, and zero delivered-pixel mismatches. They are owner-provided, unversioned, and unverified in the repository: no authoritative run ID, source/APK fingerprint, raw report, or commit was identified during roadmap preparation. Do not use them as an accepted baseline, A/B comparator, or exit evidence until CL-R11-A / CL-R12-B/C/D/E reconciliation locates and validates the source. Record the figures as unverified historical claims in the evidence ledger in the meantime.

The public PR [#52](https://github.com/bmreyes25/ClarityLink/pull/52) reports an API17 x86 hosted smoke pass, but marks the full scenario, timing, A/B, ten reconnect cycles, and failure matrix incomplete; its Offline CI currently fails on stale review-scope hashes. Treat it as partial evidence.

## Required method

- Pin the runner, Android emulator package, system image, ABI, APK/source fingerprint, and exact scenario.
- Verify the guest reports Android 4.2.2, API 17, and the intended ABI before installation or assertions.
- Run the original CL-R12 scenario and CL-R12-C stage timing with bounded, synchronized clocks.
- Measure generator cost, allocation, copies, PFD/Messenger delivery, host processing, UI work, decoder/render time, pixel validation, screenshot cost, and emulator overhead separately.
- Perform the CL-R12-D optimization as controlled baseline/candidate A/B on identical stimuli, warmup, duration, instrumentation, and environment; report distributions and resource use, not a single best run.
- Complete ten reconnect cycles and every outstanding malformed-frame/IPC/process-failure case from CL-R12-E.
- Compare decoded-frame delivery with compressed H.264/H.265 forwarding only in a separate controlled experiment; do not conflate codecs or input profiles.
- Record exact run IDs, source/APK digests, raw logs in approved private storage, sanitized receipts in GitHub, and clean emulator/process/ADB teardown.

## Exit criteria

Actual 4.2.2/API17 runtime passes; original scenario passes; stage timings and A/B results are complete; ten reconnect cycles pass; remaining failure matrix passes; queue/drop/FPS/latency/CPU/memory limits defined before final run are met; no stale frames survive; teardown is clean; CI passes on the exact reported head. Otherwise state `PARTIAL` or `NO-GO` and identify the failed gate.
