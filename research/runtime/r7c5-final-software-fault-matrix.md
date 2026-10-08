# R7C5 final software fault matrix

**Decision: software matrix not closed.** No Honda, vehicle, physical accessory, iPhone, or MFi rows were attempted.

| Software area | R7C5 evidence | Status |
|---|---|---|
| Full Python/repository checks | 902 passed, 14 skipped; simulator/self-locator checks passed | PASS |
| API17 Java and diagnostic APK build | Rebuilt with Temurin 17; APK SHA-256 `c3f9308ad912c34fe2507f633ca6c6ab064c560a42f05f6fd1c759f159bf02d5` | PASS_BUILD |
| API17 Dalvik execution in this attempt | AVD setup failed before boot (`devices.xml` missing); an ADB target later appeared and was not touched | BLOCKED |
| ARMv7/API17 production build | NDK r23c build and API17 import audit; zero unknown imports | PASS |
| Host socket adapter | ASan/UBSan and TSan scripts passed | PASS_HOST_ONLY |
| Host R7C1 integration | ASan/UBSan and TSan scripts passed | PASS_HOST_ONLY |
| Deterministic framework lifecycle races | No test barrier/controller or injected races | BLOCKED |
| Android native socket fault matrix | No runtime fault matrix; R7C4 success cases are limited to two fragmented frame deliveries | BLOCKED |
| Native socket each cycle, 100/100 cycles | Current loop uses synthetic-ingest; not rerun here | BLOCKED |
| Per-cycle complete resource oracle | Existing native counters are partial; requested complete per-cycle resource list is not asserted | BLOCKED |
| Exact-head Offline CI / CodeQL | No R7C5 commit/push; historical `0804bc0` checks apply only to R7C3 | PENDING |

There are no claims of R7C completion or R7D entry from this matrix.
