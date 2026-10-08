# R7C Display0 adapter

`PrimaryDisplayHost` exposes the Activity-owned Surface lifecycle. On create, the owner attaches a generation-scoped Type110 JNI surface; on destroy it releases that handle. The sink validates dimensions, RGBA row stride, byte count, and generation, and can clear the frame. Recreation uses a fresh token.

This is generic Android code. Window admission, orientation, and presentation policy remain the application's responsibility. Honda Display0 is `EVIDENCE_REQUIRED`; no Honda window/audio behavior is implied. `MemoryFrameSink` remains the offline host output.
