# Type111 process-isolation runtime — historical summary

**Reported status:** API17 laboratory evidence exists for injected Type111 decoder-fault recovery, View-process death, Type110 continuity, and modeled shared-session cleanup. This does not close the CL-R4 fault matrix. Detailed per-run identifiers and raw receipts are excluded from this public candidate.

The previous report states that the Type111 decoder and View shared one process in the earlier experiment; therefore it did not prove independently owned producer and sink processes. It records controlled decoder recreation, Type110 progress after View-process death, Binder/PFD delivery, H.264 fixture rendering, and final transfer/resource cleanup. A later standard run reportedly exercised crash-dialog handling, while an earlier FinalizerWatchdog failure remained unattributed and was not reproduced in that run.

CL-R4 remains partial pending independent producer/sink death and reconnection, parent-authority disappearance, reentrant teardown, and complete API17 fault-matrix evidence. The reports concern synthetic laboratory components only, not an authenticated CarPlay session or Honda receiver. `safeForHonda()` remains false.
