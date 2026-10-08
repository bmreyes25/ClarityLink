# R7C3 resource accounting — incomplete

The existing R7C2 API17 run previously reported 100 cycles with zero native diagnostic owners each cycle. It is historical evidence on the earlier APK and does not include this R7C3 socket/JNI seam. This attempt could not rebuild or run the APK because a JDK is absent.

The added socket integration checks `/proc/self/fd` before and after one successful native socket frame and checks existing native receiver/surface counters after teardown. This assertion has not executed. It is not enough for the requested full counter inventory or per-fault cleanup proof.

| Resource family | Current evidence |
|---|---|
| Receivers/streams/decoders/surface owners | R7C2 native counters, prior 100-cycle run |
| JNI global/weak refs | None owned by production bridge |
| Native socket FDs | Host adapter tests pass; proposed Android FD check unexecuted |
| Audio/input/USB/iAP2/auth | Prior Java adapter state checks; not integrated into new per-cycle counter vector |
| Retained frames / ANativeWindow | Prior R7C2 counters and Surface runtime evidence |

**Decision: `R7C_RESOURCE_CLEANUP_BLOCKED`.** Require a fresh final 100-cycle APK run with the native socket included and each resource family checked after every fault/cycle.
