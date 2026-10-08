# R7C3 framework lifecycle races — incomplete

R7C2 exercised real API17 `SurfaceHolder`, `Presentation`, `ANativeWindow` posting, and Activity start/stop lifecycle, but did not deterministically race framework callbacks with frame posting, decoder shutdown, or socket I/O. R7C4 restored JDK and pytest, ran the updated APK on Dalvik, and passed its 100-cycle harness; it still did not add the requested complete barrier-controlled race matrix.

| Race | Status | Evidence needed |
|---|---|---|
| `surfaceCreated/Changed/Destroyed` around post | PARTIAL | API17 callback barriers and per-owner zero checks |
| Presentation show/dismiss during frame | PARTIAL | Deterministic Surface callback + post barrier |
| Activity pause/resume/destroy and dual stream | PARTIAL | API17 Activity transitions synchronized against decode |
| Stop during SETUP/decode/socket I/O | PARTIAL | Barrier-controlled exact stop points and cleanup oracle |
| Audio write/pause/close | PARTIAL | Injected AudioTrack failures and deterministic close ordering |
| USB permission/device callback states | PARTIAL | Clearly labeled injected callbacks for unavailable physical device events |

R7C4 did not add barrier-controlled callback or teardown races. The original R7C3 table remains accurate for these rows; see [R7C4 decision](r7c3-r7d-entry-decision.md).

ECC review found no basis to fabricate a native-created Java callback worker. Keep `NO_NATIVE_TO_JAVA_WORKER_CALLBACK_PATH` and omit attach/detach expectations unless such a production path is added later.

**Decision: `R7C_FRAMEWORK_RACE_BLOCKED`.** No race PASS is claimed by this attempt.
