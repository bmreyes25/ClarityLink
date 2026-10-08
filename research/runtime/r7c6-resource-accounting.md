# R7C6 resource accounting

`nativeDebugResourceCounts()` reports receiver handles, surface handles, JNI
global refs, native-to-Java workers, streams, decoders, listeners, and display
owners. The 100-cycle harness asserted every reported value returned to zero
after each iteration. It also counted `/proc/self/fd` socket descriptors and
required the count to match the per-cycle baseline. Focused native read/write
tests use bounded worker joins. Activity-owned audio/input lifecycle still
needs a framework destruction test; it is not inferred from the helper's
individual open/close lifecycle checks.

Production currently owns no JNI global/weak references and creates no native
to Java worker callbacks; those rows are `NOT_APPLICABLE` by source inspection.
JNI local-reference stress on all production ref-producing paths remains to be
recorded in the final matrix.
