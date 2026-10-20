# CL-R4 Type111 producer-process result — historical summary

**Reported state:** `PARTIAL`; a Type111 producer death/restart stage reportedly passed on API17. The complete CL-R4 fault matrix remains open. Detailed process identifiers, local ADB values, raw logs, screenshots, and hashes are excluded from this public candidate.

The prior report describes a test-only Type111 producer service in a separate process from the View and compositor. It decoded existing H.264 fixtures through API17 MediaCodec and submitted frames through the existing Binder v3/PFD path. The reported run killed the producer during an in-flight transfer, observed Binder lifecycle handling and cleanup, verified a subsequent Type110 frame, restarted Type111 with a new generation, rejected stale traffic, and rendered new frames. It also reports cross-UID denials in the lab.

The report explicitly leaves sink reconnection, Type110-only failure/reconnection ownership, unexpected parent-authority process death, and reentrant teardown unverified. It does not establish authenticated Honda Type111, Honda Type110 behavior, or a Honda output interface. The reported test totals and runtime result are historical, not rerun during this publication recovery. `safeForHonda()` remains false.
