# R7C5 framework race closure

**Status: BLOCKED — `R7C_FRAMEWORK_RACE_BLOCKED`.**

ECC review of the R7C4 test activity and native bridge found no deterministic test controller or named checkpoint/latch path for Surface frame-post invalidation, Presentation dismissal, Activity stop/destroy during dual-stream operation, setup rollback, or decode shutdown. Existing Type111 and Type110 invalidation checks are sequential invalidation tests; they do not pause a frame or race a framework callback against native posting.

The requested single-run race cases and 25-iteration stress cases were not implemented or run. The existing R7C4 report's earlier API17 Dalvik pass remains historical evidence for its described test build only. In this R7C5 attempt, the emulator runner failed during AVD creation because the API17 image's `devices.xml` is missing. A subsequently visible ADB target could not be safely identified, so no further ADB or emulator interaction was made.

Required next action: restore the isolated API17 AVD metadata/runtime, then add test-only bounded latch checkpoints excluded from production and execute the named race suite. Do not infer race safety from host sanitizers or sequential Surface invalidation.
