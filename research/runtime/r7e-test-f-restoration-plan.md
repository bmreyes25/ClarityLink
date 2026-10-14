# R7E Test F — teardown and restoration

**Plan state:** `PLAN_PARTIAL` / `NOT_AUTHORIZED`  
**Risk:** Tier 3 when following display tests; restoration verification is required in every future target plan.

**Objective:** After an individually authorized target test, verify project-owned resources close and observe stock behavior afterward. This is not a claim of guaranteed factory restoration.

**Required checks:** process stopped; no project listener/socket; no decoder; no Surface/ANativeWindow/Presentation; no audio or input resource; no project temporary file; then normal center UI, instrument cluster, warnings, and audio where applicable. Capture before/after resource counters and sanitized diagnostics. R7D establishes `PROJECT_OWNED_RESTORATION` only for tested synthetic API17 paths, not Honda restoration.

**PROPOSED — NOT EXECUTED:** execute only the exact test's owned shutdown/close path; verify process and resource absence; remove only the recorded temporary artifact; verify its absence; observe stock displays/warnings/audio in stationary conditions. No generic reboot fallback; reboot only if separately justified and authorized.

**Write audit:** close/dismiss/release of project-owned resources and exact temporary-file deletion; no system partition, startup, factory binary, `jmcs`, CAN, or persistent configuration writes. Use no elevated privilege unless a separately reviewed plan proves necessity.

**Stop conditions:** any failed close, persistent process/file, warning or UI anomaly, audio loss, or mismatch triggers stop and only preapproved rollback. Exact Test F execution is coupled to the separately authorized preceding test; it grants no new test authority.

**Success:** all owned-resource checks pass and stock behavior is observed after that run. Repetition and adequate evidence remain necessary before stronger restoration claims. **Readiness:** `PLAN_PARTIAL`, blocked on a built artifact, future authorized predecessor, concrete rollback commands, and target observation.


## R7E1 update

The known Test A process name is `claritylink-target-diag`; artifact SHA-256 is `f2e12aafe221ff51e153ccc7c1b71402cf3cf0c3a4f1648fb5963e2e66cffca0`. Future rollback must target only that process and exact transferred file, verify process/file/resource absence, and observe stock center UI, cluster, warnings, and audio. The candidate path lacks live semantics evidence, so exact cleanup commands and factory restoration remain unproven. Emulator cleanup is not Honda restoration evidence.
