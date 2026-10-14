# R7E Test D — controlled single-frame rendering

**Plan state:** `BLOCKED_BY_PRIOR_TEST` / `NOT_AUTHORIZED`  
**Risk:** Tier 3, visible temporary display output.

**Objective:** After separately authorized A, B, and C passes, determine whether one project-owned static diagnostic frame can become visible on the candidate display. This is not a CarPlay, navigation, safe-area, or performance test.

**Frame design:** create offline and review before any future authorization: unique neutral geometric blocks and border/coordinate markers, explicitly marked diagnostic, with no copyrighted UI, CarPlay logo imitation, warning-like symbols, safety-state wording, map, animation, or assumed safe rectangle. Do not derive crop/safe geometry from screenshots. ECC safety review must approve the concrete frame before any run plan.

**PROPOSED — NOT EXECUTED:** acquire the already admitted Surface, clear it, post exactly one pre-reviewed frame, observe briefly, clear immediately, release Surface and Presentation, then stop. Duration value must be bounded and fixed in the later reviewed plan; no infinite render loop or background owner. R7D's 14.405 FPS is irrelevant to this one-frame question.

**Write/resource audit:** temporary visible pixels and Surface/Presentation ownership only; no persistent file, audio/input, listener, USB/iAP2, MFi, or CarPlay. Process and frame resources are bounded. Exact command is unavailable until the diagnostic artifact and prior-test results exist.

**Stop/rollback:** any warning/interrupt change, unexpected display coverage, center-display instability, cluster corruption, UI/audio instability, or cleanup failure ends the test. Clear frame, dismiss Presentation, release native resources, stop process; verify resource absence and normal center UI, cluster, warning, and audio behavior.

**Success:** human-visible frame observation with timestamp, state logs, and resource counters, classified only `HONDA_PROTOTYPE_OBSERVED` for this precise setup. **Readiness:** `BLOCKED_BY_PRIOR_TEST`; A/B/C each require separate authorization/pass. Not authorized.


## R7E1 update

The separately built APK supports explicit `SINGLE_FRAME_DIAGNOSTIC` only on an identified x86 emulator with explicit offline acknowledgement. Its generated geometric PNG is 800×480 RGBA8, SHA-256 `02730d7e4ee85464f9cd0656e7c8cb64a8427d7dbd0044ba4937c5ff8246a320`; isolated API17 test posted one frame and cleared/released it. This is not Honda safety approval. Test D remains `NOT_AUTHORIZED`; installation, admission, safe area, crop, warning coexistence, and target rollback are unresolved.
