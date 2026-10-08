# R7C3 native socket runtime — incomplete

## Scope and result

The test build now has a `CLARITYLINK_TEST_DIAGNOSTICS`-gated JNI entrypoint in `native/platform/android/jni_bridge.cpp`. It uses the production `AndroidSocketAdapter`, numeric loopback only, bounds a LAB frame, handles partial reads, and passes the parsed fixture to the existing `ReceiverGeneration`. A Java test peer fragments a synthetic Type110 frame. Production Java does not contain the test bridge class; the peer and bridge live only in `android/r7c2-test`.

The API17 x86 native test library compiled after these changes. The rebuilt Android test APK and Dalvik execution did **not** run: `/usr/bin/javac` is a macOS shim and reports “Unable to locate a Java Runtime.” The previously built APK predates this seam and is not evidence for it. Therefore `native POSIX socket runtime = PARTIAL`, not PASS.

## ECC findings

| Finding | Risk | Fix in this attempt | Verification |
|---|---|---|---|
| Java loopback did not execute the native adapter | Bionic behavior and native FD lifetime were untested | Test-only JNI route calls the existing adapter and then `ReceiverGeneration` | x86 NDK library compiles; Dalvik path unverified because APK build is blocked |
| Partial reads can split the envelope or media bytes | Truncated/misparsed LAB frame | Header and body are read with an exact-length loop and a 2 MiB cap | Source review only; runtime pending |
| Test seam could leak into production | Fault hooks or LAB ingress might become callable in normal mode | JNI exports are behind `CLARITYLINK_TEST_DIAGNOSTICS`; Java test bridge exists only in the test source set | ARM production rebuild/import audit passes; export/source-set runtime audit still pending |

## Not yet covered

Native runtime cases still need bounded execution for timeout, peer close, local shutdown, double close, port collision, refused connection, oversized input, stale generation, wrong owner, active-I/O shutdown, and per-case FD/resource zero. Server/listen/accept are not supported by the production adapter. A fragmented valid frame is the only proposed integration case and has not yet executed.
