# R7D long-run stability

**Acceptance:** at least 30 minutes continuous API17/Dalvik synthetic dual-stream load, production AndroidSocketAdapter, ReceiverGeneration, decoded H.264 frames to primary and Presentation Surfaces, AudioTrack, and final cleanup.

The first harness attempt was stopped after inspection found an absolute-zero FD assertion that ignored process baseline descriptors. The harness now records baseline socket descriptors and requires zero delta after teardown. A fresh 30-minute run is required with that corrected check and sustained AudioTrack playback.

## Final result

`R7D_LONG_RUN=PASS` on the owned API17 Dalvik emulator. Continuous synthetic dual-stream work ran for 1,800,180 ms (30 minutes), using the production `AndroidSocketAdapter`, `ReceiverGeneration`, H.264 decode/post to the primary and Presentation Surfaces, and active AudioTrack synthetic silence.

| Metric | Result |
| --- | ---: |
| Type110 / Type111 frames | 25,932 / 25,932 |
| Effective rate | 14.405 FPS per stream |
| Target schedule slots missed | 28,073 |
| Delivery failures | 0 |
| Queue depth / decoder resets / Surface recreations | 0 / 0 / 0 |
| Native owner counts after cleanup | all zero |
| Process socket FDs | baseline 5, after 5, delta 0 |
| Race controller | idle |

The emulator did not approach the 30 FPS target; the measured result is 14.405 FPS. This is reported as a performance limitation, not hidden by the duration pass. `missedTargetSlots` is the scheduler deficit (a target-rate miss count), not a count of received media frames dropped by a stream queue.

Latency values below are **minimum / median / p95 / maximum**, in milliseconds. Socket-to-post includes the loopback test peer, fragmentation, production socket read, decode, and Surface post. Media-to-display is a software pair-completion proxy; it is not photon or scanout latency.

| Latency | Min | Median | P95 | Max |
| --- | ---: | ---: | ---: | ---: |
| Type110 socket-to-post | 13.262 | 31.140 | 48.810 | 1,611.592 |
| Type111 socket-to-post | 15.489 | 32.462 | 49.695 | 874.635 |
| Type110 decode | 0.669 | 0.876 | 4.184 | 479.357 |
| Type111 decode | 0.664 | 0.905 | 4.417 | 224.835 |
| Type110 Surface post | 2.179 | 10.842 | 21.503 | 698.744 |
| Type111 Surface post | 2.087 | 11.424 | 21.418 | 540.020 |
| Dual-stream media-to-display proxy | 36.985 | 63.876 | 93.817 | 2,486.234 |

Across 86 resource samples, PSS ranged from 8,623 to 15,470 KiB. Native heap stayed between 13,344,968 and 13,345,112 bytes, socket FD count stayed at five, and project thread count stayed at one. The bounded per-frame latency lists account for some expected test-process memory growth over the fixed run. Cleanup returned native owner counts to zero and restored the socket FD baseline.

Evidence: [`/tmp/claritylink-r7d-long-run-final.log`](/tmp/claritylink-r7d-long-run-final.log) and [`/tmp/claritylink-r7d-long-run-final-runtime.log`](/tmp/claritylink-r7d-long-run-final-runtime.log).
