# R7D performance observations

The corrected 30-minute API17 Dalvik run completed with 25,932 frames per stream and 14.405 effective FPS against a 30 FPS target, with 28,073 missed schedule slots and zero delivery failures. It demonstrates sustained real socket/decode/Surface work but does not meet the requested near-30-FPS representative target. The emulator harness performs a fragmented loopback transaction for each frame; this is an intentionally demanding test path and contributes overhead. No claim is made that this rate predicts Honda hardware performance.

The reported min/median/p95/max socket-to-post latencies were 13.262/31.140/48.810/1,611.592 ms for Type110 and 15.489/32.462/49.695/874.635 ms for Type111. The media-to-display pair completion proxy was 36.985/63.876/93.817/2,486.234 ms. These are software timings, not physical display scanout measurements. Full latency and resource results are in `r7d-long-run-stability.md`.

**Status:** durability run passed; target-rate performance remains below goal and is explicitly unresolved.
