# R7E5A — A0-W Authorization Packet (Not Authorized)

**Status:** `R7E_A0W_EXECUTION_PACKAGE_READY` — awaiting a separate, explicit user authorization. This packet does not authorize any target command. A0-W and Test A have not been executed.

## Purpose and reviewed A0-R evidence

A0-W is a Tier 2, one-file transfer/delete preflight. It is needed because A0-R established destination metadata, ordinary shell identity, mount flags, and utility availability, but did not establish successful write, ADB sync transfer, deletion, or absence verification. A0-R evidence was reviewed from the private local run and summarized in [the sanitized result](r7e5-a0r-result.md); the private evidence remains local and unmodified.

A0-R result was `A0R_PASS_FOR_REVIEW`: Android 4.2.2 / API 17 / `armeabi-v7a`, UID 2000, `/data/local/tmp` observed as `drwxrwx--x shell:shell`, `/data` ext4 `rw` with `nosuid,nodev` and no observed `noexec` flag. SELinux visible state was unavailable and was not inferred. Tool metadata classifications were `TOOLBOX_PRESENT`, `RM_PRESENT`, `PS_PRESENT`, `KILL_PRESENT`, `MD5_PRESENT`, and `CHMOD_PRESENT`; these were metadata reads only. A0-R reported zero writes and unchanged stock state. Its operator-observed power text was recorded verbatim; this packet does not reinterpret it as ACC/ON/READY.

## Exact package identity

- Collector: `tools/r7e5a_a0w_collector.py`
- Collector source SHA-256: `54001498a474c0233ffa7e27eced9340834a91672d670c4df05ce2acf9410d5b`
- Plan version: `R7E5A-A0W-COMMAND-SET-1`
- Manifest: [r7e5a-a0w-plan-manifest.json](r7e5a-a0w-plan-manifest.json)
- Manifest SHA-256: `db71f46b965d93f9005fdc9c1c9a538e037545f92710dc40ec22ca48aa4c9cb5`
- A0-R binding: collector commit `47605adad4e83faa8e05e028cd46282848546139`; source SHA-256 `8693ac5d9165343bb94b9f56be4c4d0b8f3666884361e2f2d07f65a4b53a9c1d`; manifest `R7E4-A0R-COMMAND-SET-1`; manifest SHA-256 `962b25fca36dabde11f2406da1e5d898a0fe5c3a49f78f2bd00f292910442004`.
- Package review base: PR #19 head `361a8e37f1ac4567d40fe0b801a4acd633fad696`; R7E5A final exact head and checks are recorded in the R7E5A step report after push.

Any change to the A0-W collector source, marker bytes/mode/path, command set, or manifest bytes invalidates this packet’s binding and requires a new review. A changed manifest has a new SHA-256 and supersedes the value above.

## Marker and exact destination

- Host file: `build/r7e/a0w/claritylink-a0w-marker.txt` (ignored local build data)
- Exact ASCII bytes: `ClarityLink A0-W inert transfer marker\nR7E5A\nNO EXECUTION\n`
- Length: 58 bytes; mode: `0644`; regular file, non-executable
- SHA-256: `6b0693fdcff5be76f10a0886ee0e82efeed070e493abaf28633775d8979706df`
- MD5: `395de139036f88640ad5acf7c6f6230e` (transport consistency only)
- Exact remote path: `/data/local/tmp/claritylink_a0w_r7e5a_5f9ffbe9dc38eaa3f98fb387f35109bd.probe`

The collector requires the host marker to remain byte-identical, regular, and exactly mode `0644`; the target parent must still match the observed exact mode and owner/group. It does not create directories or overwrite by issuing shell redirection.

## Frozen target command sequence

All commands have 15-second timeouts, zero retries, and no fallback. The runtime requires the separately reviewed source and manifest hashes, an authorization reference, direct operator observations, safe parked/stationary/display/cluster/warning confirmations, confirmation that the sole listed target is the intended Honda, and `--exclusive-adb-window-confirmed`. That last flag confirms the operator has excluded concurrent ADB writers during the lifecycle. Runtime flags are software gates, not authorization.

1. `adb devices` — require exactly one `device` target.
2. `adb -s TARGET shell ls -ld /data/local/tmp` — revalidate exact parent metadata.
3. `adb -s TARGET shell ls -l /data/local/tmp/claritylink_a0w_r7e5a_5f9ffbe9dc38eaa3f98fb387f35109bd.probe` — require exact, recognized not-found response; any existing path or ambiguous failure stops before push.
4. `adb -s TARGET push build/r7e/a0w/claritylink-a0w-marker.txt /data/local/tmp/claritylink_a0w_r7e5a_5f9ffbe9dc38eaa3f98fb387f35109bd.probe` — the only transfer/write attempt.
5. `adb -s TARGET shell ls -l /data/local/tmp/claritylink_a0w_r7e5a_5f9ffbe9dc38eaa3f98fb387f35109bd.probe` — require regular file, exact 58-byte size, `shell:shell`, and non-executable `0644` mode.
6. `adb -s TARGET shell /system/bin/md5 /data/local/tmp/claritylink_a0w_r7e5a_5f9ffbe9dc38eaa3f98fb387f35109bd.probe` — require the frozen MD5. A0-R proved the utility was present; an invocation failure is a stop condition.
7. `adb -s TARGET shell /system/bin/rm /data/local/tmp/claritylink_a0w_r7e5a_5f9ffbe9dc38eaa3f98fb387f35109bd.probe` — the only cleanup mutation; exact path, no flags or wildcard.
8. `adb -s TARGET shell ls -l /data/local/tmp/claritylink_a0w_r7e5a_5f9ffbe9dc38eaa3f98fb387f35109bd.probe` — require the same exact not-found response to establish absence.

The collector attempts exact cleanup and verifies absence after any push attempt, including a reported push failure or timeout. Cleanup failure or unverified absence is a hard stop; no alternate cleanup is allowed. The operator must report the post-run state, with `STOCK_STATE_UNCHANGED` accepted only when actually true.

## ADB sync caveat and stop conditions

AOSP Android 4.2.2 sync-server `do_send` unlinks the exact destination before receiving the new file. Therefore, the read-only pre-existence check is not an atomic no-overwrite guarantee. The future operator must ensure an exclusive ADB window with no concurrent writer and stop if that cannot be established; the unique fixed path and absence check reduce accidental collision risk but do not remove the race. See [AOSP 4.2.2 `file_sync_service.c`](https://android.googlesource.com/platform/system/core/%2B/android-4.2.2_r1.2/adb/file_sync_service.c) and [AOSP 4.2.2 `ls.c`](https://android.googlesource.com/platform/system/core/%2B/android-4.2.2_r1.2/toolbox/ls.c).

Stop for package/hash mismatch, zero/multiple/offline/unauthorized targets, unexpected parent metadata, existing or ambiguously absent destination, command failure/timeout, push or metadata/MD5 mismatch, cleanup/absence failure, or any change in vehicle/UI/cluster/warnings/audio. No troubleshooting, connection management, retry, fallback, or additional command is permitted.

## Scope and authorization boundary

A0-W can establish only that the exact inert marker transferred, was observed with expected metadata and transport digest, was removed, and was verified absent. It does not establish executable mapping/launch, ClarityLink operation, display behavior, or any later integration behavior.

**A0-W: NOT AUTHORIZED. Test A: NOT AUTHORIZED.** No push, target write, marker creation on Honda, execution, chmod, display operation, USB/iAP2 operation, root operation, or process control is authorized by this packet. A0-W requires a separate explicit user authorization binding to these exact hashes and commands. Test A requires a separate future review and authorization after A0-W evidence review.
