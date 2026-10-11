# R7E6A Test A readiness decision

**Decision:** `R7E_TEST_A_EXECUTION_PACKAGE_READY`.

**Next:** `READY_FOR_EXPLICIT_TEST_A_AUTHORIZATION`.

R7E6A corrected the collector's legacy ADB absence checks. The pre-transfer and final gates now require exact-path `ls -ld` ENOENT output and never treat an empty response or host status as absence. MD5 parsing requires one exact digest/path line. Cleanup after diagnostic start is allowed only after the exact lifecycle records and both exact PIDs absent are verified; otherwise the collector stops without removing a possibly executing file and writes a private, identifier-redacted failure record.

The focused API17 Android 4.2.2 x86 emulator probe observed: missing-path `test -e` returned host status 0 with empty output; exact `ls -ld` emitted the frozen path's ENOENT line; regular file, symlink, and directory states did not match absence; exact removal and final ENOENT passed. No diagnostic was run in this probe. The production ARMv7 artifact and staging bytes/modes remain unchanged.

The revised collector has 42 passing fake-ADB tests covering absent/present/ambiguous path states, digest/path binding, process uncertainty and cleanup, timeout handling, authorization gates, and no retry/fallback. Full repository checks and exact-head hosted checks are recorded in the R7E6A report.

Test A remains **NOT_EXECUTED** and **NOT_AUTHORIZED**. This readiness decision is not permission to run it. A separate explicit user authorization must bind the new collector and manifest hashes and all operator gates. Test B remains not authorized and cannot auto-start. No Honda command or physical Android contact occurred during R7E6A.

See the [current authorization packet](r7e6-test-a-authorization-packet.md), [current manifest](r7e6-test-a-plan-manifest.json), [preserved prior package](r7e6-test-a-authorization-packet-historical.md), [API17 absence probe summary](r7e6a-api17-absence-probe.md), and [R7E6A report](../../step-reports/43t1-r7e6a-test-a-collector-safety-closure.md).
