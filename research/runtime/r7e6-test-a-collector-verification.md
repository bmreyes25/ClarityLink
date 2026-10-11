# R7E6A Test A collector verification

The dedicated collector is `tools/r7e6_test_a_collector.py`, SHA-256 `083ff20d474a84ceaa7bd2c6a9514abd51b1f8a037c1500c31ae754890f5d750`, frozen as manifest `R7E7A-TEST-A-COMMAND-SET-2`, SHA-256 `e498971cf45219832827fd77ec2f7f71a0829cdc9b0307d5a564213459171c21`. It prints `NOT_AUTHORIZED` by default; `--dry-run` prints the frozen command plan and performs zero ADB operations. The runtime flag is only a software gate, not user authorization.

The new `R7E7A-TEST-A-COMMAND-SET-2` manifest SHA-256 is `e498971cf45219832827fd77ec2f7f71a0829cdc9b0307d5a564213459171c21`. It binds the unchanged 7,904-byte ARMv7/API17 artifact (SHA-256 `9e20d1ad715be6c9974f9a89e1aa310283bc128f87350fb05cb224b8e247c063`, MD5 `6137a693a77646aaf9a4cf0f351731d4`) and the exact remote path in the manifest. The 0555 staging copy remains byte-identical.

Focused fake-ADB coverage: 49 passing cases. This includes legacy host-zero/empty-output rejection; strict exact-path ENOENT; existing regular-file, symlink, and directory rejection; permission, command-not-found, mixed, extra, and unknown output rejection; MD5 filename binding and malformed/multiple output; procfs-positive-control failures; empty, malformed, duplicate, and extra process sentinels; process-state uncertainty; host timeout; exact cleanup and final absence; default-disabled authorization; target identity; and no retry, fallback, or Test B. Same-shell procfs controls also passed on isolated API17 x86; see [R7E7A review](r7e7a-test-a-identity-proc-review.md).

The isolated Android 4.2.2/API17 x86 regression observed that missing-path `test -e` returned host status 0 with empty output, and verified exact `ls -ld` absence/presence distinctions for a regular file, symlink, and directory, followed by exact removal and final ENOENT. See [probe summary](r7e6a-api17-absence-probe.md).

The collector requires exact ADB version, one supplied target, exact parent metadata, strict exact-path absence, one push, exact remote metadata/mode, a single expected MD5 line bound to the exact path, successful supervisor lifecycle records and both PIDs absent for each mode, exact cleanup, strict final absence, and direct stock-state confirmation. A timeout or uncertain process state stops further target commands and does not attempt executable removal. No external `ps`/`kill`, wildcard, `chmod`, retry, fallback, root, or automatic Test B is present.

Test A remains `NOT_AUTHORIZED` and `NOT_EXECUTED`. No Honda command or physical Android contact occurred in R7E6A.
