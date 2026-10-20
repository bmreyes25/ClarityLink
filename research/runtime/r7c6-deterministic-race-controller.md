# R7C6 deterministic race controller

The API17 diagnostic library contains one generation- and stream-bound native
checkpoint controller (`native/platform/android/r7c6_race_controller.*`). It
uses a mutex, condition variable, and bounded waits. Java arms, awaits, and
releases checkpoints through `R7C6TestBridge`; tests use latches and bounded
joins. Checkpoints cover primary/secondary setup allocation, primary/secondary
decode before post, and active socket read/write. Clearing releases blocked
hooks. The controller is linked only by the explicit API17 diagnostic x86
build; the production ARM build does not define `CLARITYLINK_TEST_DIAGNOSTICS`
or link the controller.

Setup cancellation, decode cancellation, Type111 Surface loss, Presentation
dismiss, and socket read/write shutdown passed individual Dalvik cases in the
captured runs. Type110 framework Surface destruction, actual Activity
destruction during dual-stream work, and the required 25-iteration stress set
remain unverified. This document does not mark the full framework gate passed.
