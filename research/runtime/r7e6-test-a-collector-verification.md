# R7E6 Test A collector verification

The dedicated host collector is `tools/r7e6_test_a_collector.py`. Its SHA-256 is `5837624209be870b60027041235428e5839dcf4b85055bbdfd83cd759794235e`. It prints `NOT_AUTHORIZED` by default. `--dry-run` reports the frozen command plan with zero ADB operations. The `--execute-authorized-test-a` option is only a code gate and is not user authorization; a future separate user authorization must bind both collector and manifest hashes.

Fake-ADB coverage: 23 passing cases. It covers default and dry-run behavior, target count/identity, destination mismatch and pre-existing exact path, push failure, size/mode/writable/executable rejection, MD5 mismatch, version and self-test failures/timeouts, process-present and ambiguous process reports, exact cleanup success/failure, final absence failure, stock-state mismatch, no retry/fallback, and excluded Display1/CarPlay/Test B actions.

The collector requires exact host ADB version `37.0.1-15733141`, an explicit exact serial matching the sole `device` entry, all pre-execution operator gates, the local frozen artifact and mode/hash identity, exact remote metadata and MD5, exact supervisor PID reports and absence checks, exact cleanup and absence, and direct post-test stock-state confirmation. It uses no `chmod`, external `ps`/`kill`, wildcard, retry, fallback, or automatic Test B path. Timeout is a stop-and-review anomaly with no further target command.

The collector was not run against Honda or any physical Android device. The manifest and authorization packet are frozen for separate review; Test A remains `NOT_AUTHORIZED`.
