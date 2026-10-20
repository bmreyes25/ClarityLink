# R7C5 resource accounting

**Status: BLOCKED for complete acceptance accounting.**

Historical R7C4 evidence reports its native counters returning to zero after each of 100 synthetic-ingest cycles, and socket descriptor count returning to its measured baseline around the separate native socket exercise. R7C5 did not rerun Android cycles.

The current JNI diagnostic array does not expose every requested owner independently. The required full oracle (receiver generations, streams, decoders, security contexts, native socket FDs, transport owners, Surface sinks, ANativeWindow owners, frames, JNI handles/refs, audio, input, USB, iAP2, and auth) is not asserted after every acceptance cycle. JNI source inspection finds no production `NewGlobalRef`, `NewWeakGlobalRef`, or native-to-Java worker callback path; classify these as `NOT_APPLICABLE` for the current implementation, subject to source changes. Host sanitizers passed but are not emulator leak evidence.

ECC ownership review: do not treat monotonic identifier counters as retained owners; keep owner counts distinct, expose a test-only snapshot, and fail immediately with the cycle number on any nonzero retained owner.
