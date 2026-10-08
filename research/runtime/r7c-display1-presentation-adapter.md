# R7C Display1 Presentation candidate

API17 `DisplayManager.getDisplays()` supplies candidates; display ID, real dimensions, refresh rate, rotation, name, and validity are inventoried. Public API17 display type is recorded UNKNOWN; no ID/order assumption is made. An evidence-backed selector must match exactly one valid display or selection fails.

`SecondaryDisplayHost` tracks context creation, Presentation construction, show acceptance, Surface creation, and first frame separately. Admission errors are reported by operation and exception type. Surface loss detaches the JNI sink. Generation changes require teardown and a fresh token. Type111 failure does not route to Display0.

Warning policy and a non-test layout are required before showing the candidate. `FULL_FRAME_TEST_LAYOUT` is test-only and rejected for target admission. Honda Display1 admission remains `EVIDENCE_REQUIRED`.
