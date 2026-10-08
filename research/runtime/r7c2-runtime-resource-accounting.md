# R7C2 runtime resource accounting

The test-only native diagnostic method reports eight project-owned resource counts without credentials or phone identity. The harness asserts active ownership during the dual-stream session, then asserts every counter is zero after teardown in each cycle. It also validates stale receiver calls after release. The cycle loop ran 100 times on Dalvik and checked each cycle separately.

Counters cover receiver and surface handles, generation-owned receiver/stream resources, decoders, surface/native-window owners, and frame ownership available at the native test seam. Java adapters close audio, input, socket, USB, iAP2 and authentication state through their own APIs. These Java state assertions are not all represented in the native counter vector; do not interpret that vector as a kernel-wide resource audit.

ECC finding: observing only final totals could conceal one leak followed by an accidental decrement. Fix: check native zero after every cycle and check dual-stream nonzero ownership before disconnect. Host R7C1 registry/surface tests separately stress concurrent allocation and invalidation under ASan/UBSan/TSan.

Classification: `ANDROID_API17_DALVIK_RUNTIME_CONFIRMED_X86` for per-cycle native ownership counters; host sanitizer evidence remains `HOST_NATIVE_CONFIRMED`. No Android sanitizer was run.
