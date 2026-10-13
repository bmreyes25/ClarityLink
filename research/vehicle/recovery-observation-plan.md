# Recovery observation plan — V1 through V4

## Current decision

`PHASE_S_BLOCKED`, `CURRENT_PROCESS_SAFETY_UNKNOWN`, `PHASE_C_NO_GO`, and `TEST_A_BLOCKED_WITH_EXACT_REASON`. The latest host-only R7E7I assessment found no defensible historical clock-error upper bound. Ordinary unauthenticated NTP agreement is not a trusted historical or current-clock attestation. Do not fill the older Phase S packet's illustrative error values.

The old invocation completion record has no old PID or boot ID. If authentic time evidence later permits the frozen Phase S comparison, a successful later-boot inequality can support only that the earlier invocation could not survive that boot. It cannot show current process absence or exclude a later relaunch.

## V1 — Phase S historical termination

The only command sequence considered is the existing frozen sequence in [Phase S manifest](../runtime/r7e7i-phase-s-manifest.json):

1. `adb version`
2. `adb devices`
3. `adb -s <EXACT_SERIAL> shell /system/bin/cat /proc/sys/kernel/random/boot_id`
4. `adb -s <EXACT_SERIAL> shell /system/bin/cat /proc/uptime`
5. `adb -s <EXACT_SERIAL> shell /system/bin/cat /proc/sys/kernel/random/boot_id`

No command is runnable now. Pre-run gates include a genuine historical-time source with explicit maximum error; a fresh current-host clock bound; the reviewed signed attestation bound to old-record, collector, and manifest hashes; independently verified reviewer key/provenance; exact frozen package and intended serial; current parked/operator checks; exclusive stable ADB ownership; and a new single-use authorization. Any failed gate means stop without ADB. Timeouts, malformed data, clock step, boot mismatch, or identity mismatch stop immediately; zero retries/fallbacks. A successful result must retain the conservative inequality and only assert historical termination.

## V2 — current process and relaunch evidence

There is no runnable V2 command package. The offline parser at `tools/r7e7i_current_process_evidence.py` describes supplied evidence; it does not collect Honda `/proc`. Complete shell visibility, executable identity, mapping/file-descriptor coverage, PID generation, and absence of unreadable processes have not been demonstrated on this Honda. Android 4.2.2 permissions may restrict visibility. Empty `ps` is not proof. `pidfd` methods are not a compatible assumption for this API level.

Before proposing commands, offline work must establish whether a narrow Android 4.2.2 shell procedure can acquire exact-path device/inode, per-process executable links, maps, open references, boot identity and stable inventories without a broad process sweep. It also needs an independent review of relaunch routes. If a completeness argument cannot be made, do not run a partial scan and call it clear; record the exact permission/coverage limitation and keep `CURRENT_PROCESS_SAFETY_UNKNOWN`.

If a future tool is justified, it must be a separately frozen read-only manifest with exact serial gate, command grammar, bounded timeouts, private evidence, and stop-on-first-error. It must not follow V1 automatically and must never request root, ptrace, signals, kills, or process-wide mutation.

## V3 — exact-path cleanup

The existing [conditional Phase C manifest](../runtime/r7e7i-phase-c-cleanup-manifest.json) targets only `/data/local/tmp/claritylink_target_diag_r7e6a_4b91c27e6d3a508f`, with historical expected regular-file metadata 7904 bytes, mode `0555`, `shell:shell`, MD5 `6137a693a77646aaf9a4cf0f351731d4`. Those old observations do not prove current identity or absence. Its proposed write is one exact-path `/system/bin/rm`; that command is not authorized and is not included as an executable step in a new package.

Gates are fresh exact file identity/digest; sufficient V2 current reference evidence; independently reviewed no-relaunch basis; unchanged frozen collector/manifest hashes; exclusive ADB and parked state; and a new independent single-use authorization. Any mismatch, permission gap, timeout, unexpected relaunch, ambiguous result, or post-delete verification failure means `PHASE_C_NO_GO`; never retry, wildcard, broaden, or run Test A. Path unlink does not terminate an already open executable.

## V4 — ARMv7 Test A

No Test A package is runnable. The old artifact remains identified in the existing manifest (7904 bytes, SHA-256 `9e20d1ad715be6c9974f9a89e1aa310283bc128f87350fb05cb224b8e247c063`), but target state is unresolved. The repetition-52 emulator event remains a failure/inconclusive record: `SELF_TEST_PASS` was present, but host timeout occurred without confirmed supervisor reap or guest exit. The bounded host cleanup fix and successful short emulator rehearsals do not establish the old run's cause.

Before a future distinct Test A review: resolve V1–V3, confirm exact remote absence, re-verify production and package hashes, preserve the 12-second host command watchdog unless new evidence justifies another design, require both guest status and supervisor reap markers, and freeze private evidence, timeouts, one-stop behavior and restoration checks. A host timeout is never guest success. Test B remains out of scope. Test A requires a separate new authorization and cannot auto-follow cleanup.

## Required recovery and evidence handling

Each future session begins only after the prior scope is stopped and reviewed. Use exact serials, an already stable connection, one command owner, bounded commands, no retries/fallbacks, private mode-0600 evidence in mode-0700 directories, and hashes for raw receipts. Preserve failures and never overwrite prior evidence. Do not use power cycling, battery disconnection, forced reboot, root, or process termination to manufacture proof.
