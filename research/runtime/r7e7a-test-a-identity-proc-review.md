# R7E7A Test A identity and procfs review

**Scope:** Offline package reconciliation and legacy API17 process-absence review. No Honda ADB, physical Android, Test A execution, or vehicle writes.

## Identity reconciliation

The earlier R7E7 prompt contained the obsolete R7E6 destination `/data/local/tmp/claritylink_target_diag_r7e6_7f1a3c9d2b6e40a8`. The current R7E6A package consistently names `/data/local/tmp/claritylink_target_diag_r7e6a_4b91c27e6d3a508f` in the collector, manifest, current authorization packet, and dry run. This is classified as `EXTERNAL_PROMPT_PATH_MISMATCH`; the frozen R7E6A path did not conflict internally.

## Process absence review

The existing sentinel required exact output and rejected empty output, so it was not the same defect as the prior remote-file absence check. However, two successful `test ! -e /proc/<pid>` results alone do not prove that `/proc` is available and visible. Linux procfs supports `hidepid` modes that can hide process directories from other users. The diagnostic and its supervisor run as the ADB shell user, so their PIDs share the invoking shell's UID; a same-shell positive control is still required to reject missing/unusable procfs. The [Linux procfs documentation](https://docs.kernel.org/filesystems/proc.html) describes `/proc/self` and `hidepid`; [proc(5)](https://man7.org/linux/man-pages/man5/procfs.5.html) describes how `hidepid` controls access to `/proc/<pid>` directories.

The frozen process check now first requires `/proc/$$` to be a directory, `/proc/$$/stat` readable, and `/proc/self/stat` readable. It then requires both reported diagnostic PIDs to be absent and emits exactly one PID-bound success sentinel. The collector validates reported PID fields as decimal integers greater than one before constructing this command. It never signals or otherwise modifies a process. A visible PID, unavailable control, host timeout, empty output, malformed output, or any extra output blocks and preserves uncertain state without cleanup.

`hidepid=1/2` hides or restricts other users' PID views; it does not hide a process from its same-UID shell under the normal procfs model. This is a Linux procfs expectation, not a claim about Honda-specific kernel configuration. The positive control proves procfs visibility for the shell itself, while same-UID execution is established by the Android shell launch model. A procfs namespace/mount anomaly or failure of the positive control fails closed.

PID reuse cannot cause the collector to signal another process because no kill operation exists. If an unrelated process reuses a reported PID and is still visible at check time, absence fails closed. If reuse occurs and exits before observation, the original process was already gone; the check makes no ownership claim about the reused process. Exact supervisor start/reap records remain required before this check.

## Evidence and decision

- Collector mode: default remains `NOT_AUTHORIZED`; dry run remains zero ADB operations.
- Process check: now includes same-shell procfs positive controls before exact PID absence checks.
- Collector fixtures: 49 passed.
- API17 emulator: proc-only matrix passed on Android 4.2.2/API17/x86. `/proc/$$`, its `stat`, and `/proc/self/stat` were accessible; a visible live PID prevented the absence marker; an inaccessible positive-control path prevented it; and a waited/reaped child PID was absent. The dedicated emulator and private ADB server were cleaned up with no cleanup failures. Raw run evidence is private/ignored at `build/r7e6/runs/api17-runtime-93346acbe164.json`.
- Harness note: the first proc-only attempt stopped on a test-harness expectation error after confirming the positive control. It did not run the remaining matrix. The corrected focused run above passed; both runs used run-owned emulator/server resources and cleaned them up.
- Artifact: unchanged; SHA-256 `9e20d1ad715be6c9974f9a89e1aa310283bc128f87350fb05cb224b8e247c063`; MD5 `6137a693a77646aaf9a4cf0f351731d4`; 7,904 bytes; staging mode `0555`.
- Test A: `NOT_AUTHORIZED`, `NOT_EXECUTED`.
- Honda commands/writes: zero.

ECC review used the repository's ECC security-review and Python-testing guidance. Independent ECC review was unavailable; this is manual ECC-guided review only.
