# R7D 500-session churn

The R7D churn mode creates and tears down 500 synthetic dual-stream `ReceiverGeneration` sessions against actual emulator Surfaces. Both streams decode/post once per session. It checks all native owner counters and the socket descriptor baseline after every session and records PSS/native heap every 50 sessions.

**Status:** run pending.


## Result

The completed run passed 500/500 sessions. All eight native counters returned to zero every cycle; process socket descriptors stayed at the recorded baseline of 5 (delta zero) every cycle. Sampled PSS values were 6948, 6889, 6972, 7036, 7133, 7197, 7217, 6985, 7045, and 7113 KiB at cycles 50 through 500. Native heap was about 10.59 MiB from cycle 100 onward. This run shows no unbounded trend over 500 emulator sessions.

Evidence: [`/tmp/claritylink-r7d-churn-runtime.log`](/tmp/claritylink-r7d-churn-runtime.log) and [`/tmp/claritylink-r7d-churn-final.log`](/tmp/claritylink-r7d-churn-final.log).
