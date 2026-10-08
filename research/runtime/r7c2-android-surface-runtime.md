# R7C2 Android Surface runtime

The test application obtains its primary Surface through the production `PrimaryDisplayHost` and secondary Surface through the production API17 `SecondaryDisplayHost`/`Presentation` candidate. It passes both Java `Surface` objects through JNI. Production `ANativeWindow_fromSurface`, geometry setup, lock, bounded RGBA row copy, unlock/post, acquire, and release are exercised by actual R7B H.264 decode and output.

Two independently decoded synthetic fixtures produce Type110 and Type111 frames on distinct Android Surfaces in the same LAB session. Generation, stream, and surface tokens are checked. Invalid null Surface and stale handle are rejected. Across 100 cycles, replacement handles are used, both streams render, disconnect releases native owners, and every debug native counter returns to zero. A Type111 surface-handle invalidation rejects later secondary output while Type110 remains active; primary invalidation closes the session.

ECC review: checked dimensions/stride/byte products and row-copy bounds remain in `SurfaceSinkCore`; sink mutex serializes present/clear/invalidate; no Java/UI call occurs under receiver locks. The native wrapper retains its own ANativeWindow reference and drops the temporary JNI conversion reference. Runtime validated actual posts and deterministic stream-level invalidation.

Limit: the Activity does not race Android's actual `surfaceDestroyed` callback against an in-flight native post using a controllable barrier, nor inject `ANativeWindow_lock`/unlock failures on Dalvik. Host SurfaceSinkCore fault and race tests remain the evidence for those branches. Therefore the API17 post path is runtime-confirmed, while exhaustive framework callback race closure remains partial. No Honda Surface was used.
