# R7E7A Test A readiness decision

**Decision:** `R7E_TEST_A_EXECUTION_PACKAGE_READY`, subject to exact-head hosted checks.

**Next:** `READY_FOR_EXPLICIT_TEST_A_AUTHORIZATION`.

R7E7A reconciled the previous prompt's obsolete destination as an external instruction mismatch; the current frozen package path is consistently `/data/local/tmp/claritylink_target_diag_r7e6a_4b91c27e6d3a508f`. It also added a positive procfs control before exact process-absence checks. The invoking shell's `/proc/$$` directory and readable stat and `/proc/self/stat` must be accessible before both diagnostic PIDs can be declared absent. Empty or malformed sentinel output still fails closed. Cleanup after diagnostic start is allowed only after the exact lifecycle records and both exact PIDs absent are verified; otherwise the collector stops without removing a possibly executing file and writes a private, identifier-redacted failure record.

The focused API17 Android 4.2.2 x86 emulator probe observed: missing-path `test -e` returned host status 0 with empty output; exact `ls -ld` emitted the frozen path's ENOENT line; regular file, symlink, and directory states did not match absence; exact removal and final ENOENT passed. No diagnostic was run in this probe. The production ARMv7 artifact and staging bytes/modes remain unchanged.

The focused API17 x86 procfs review passed same-shell `/proc` controls, detected a visible live PID, rejected absent positive-control paths, and detected a reaped PID as absent. The revised collector has 49 passing fake-ADB fixtures covering procfs-control failure, PID-present/uncertain state, exact sentinel formats, cleanup policy, timeout handling, authorization gates, and no retry/fallback. Full repository tests and exact-head hosted checks are required on the R7E7A head.

Test A remains **NOT_EXECUTED** and **NOT_AUTHORIZED**. This readiness decision is not permission to run it. A separate explicit user authorization must bind the new collector and manifest hashes and all operator gates. Test B remains not authorized and cannot auto-start. No Honda command or physical Android contact occurred during R7E7A.

See the [current authorization packet](r7e6-test-a-authorization-packet.md), [current manifest](r7e6-test-a-plan-manifest.json), [procfs review](r7e7a-test-a-identity-proc-review.md), [preserved prior package](r7e6-test-a-authorization-packet-historical.md), and [API17 absence probe](r7e6a-api17-absence-probe.md).
