# R7C2 secondary display runtime

The API17 AVD uses AOSP's synthetic overlay-display setting `800x480/160`, restored to empty before shutdown. Actual `DisplayManager.getDisplays()` returned Display0 480×800 and overlay Display1 800×480, both valid. The Java discovery and candidate selection code ran. The adapter emitted distinct states for enumeration, context creation, Presentation construction, Presentation shown, and Surface creation. A real API17 `Presentation`, `SurfaceView`, `SurfaceHolder` callback, JNI Surface conversion, and first Type111 frame were exercised.

This is `ANDROID_API17_DALVIK_RUNTIME_CONFIRMED_X86`. The full-frame test layout is synthetic and `NOT_HONDA_SAFETY_APPROVED`; the policy remains warning-UNKNOWN/fail-closed outside explicit test-only mode. It is not evidence of Honda Display1 window admission, warning coexistence, or safe area.

ECC finding: conflating a listed display with usable/admitted output could cause unsafe secondary routing. Fix: preserve separate state transitions and fail closed on ambiguous/absent display or presentation failure; Type111 failure never falls back to Display0. Verification: runtime state trace and separate stream outputs. Honda admission and warning visibility remain `EVIDENCE_REQUIRED`.
