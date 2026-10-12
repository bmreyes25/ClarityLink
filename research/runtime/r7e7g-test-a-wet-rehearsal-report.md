# R7E7G Test A offline wet rehearsal

## Scope and baseline

Starting HEAD `7609b6f6b1c2ad9af5fc13db317e8a7d548d2e28` on PR #19. The milestone used only local simulation and an isolated Android 4.2.2/API17 x86 emulator. No Honda ADB command, write, executable launch, recovery inspection, or cleanup occurred. The prior Honda attempt remains classified `TEST_A_PROCESS_STATE_UNCERTAIN`: one push and MD5 verification succeeded, `--version` was invoked once, then the malformed nested-shell process check returned empty output. No self-test or cleanup followed. The current Honda file and process states remain unknown.

Frozen production Test A identities are unchanged:

| Item | Identity |
|---|---|
| Collector | `tools/r7e6_test_a_collector.py`, SHA-256 `acee02afd1eaef3aab5b4d4b24ded8044fce67e6461c1d4883b552c87465deb5` |
| Manifest | `R7E7F-TEST-A-COMMAND-SET-5`, SHA-256 `20e93f4692e423851b1195d7c52db1c42e5088126faee2db8c993622611ab6c9` |
| ARMv7 artifact | SHA-256 `9e20d1ad715be6c9974f9a89e1aa310283bc128f87350fb05cb224b8e247c063`; MD5 `6137a693a77646aaf9a4cf0f351731d4`; 7904 bytes; staging mode `0555` |
| Exact prior path | `/data/local/tmp/claritylink_target_diag_r7e6a_4b91c27e6d3a508f` |

The original private Honda failure evidence was read without modification. Historical A0-R/A0-WR and R7E7C sanitized output guided the fake directory listing, CRLF, toolbox file listing, stderr push line, two-space MD5, and exact-path ENOENT responses. Synthetic negative variations are labeled as test fixtures. The fake success response does not claim an observed Honda 7904-byte transfer line.

## Layer A: full collector simulation

`tools/r7e7g_test_a_wet_rehearsal.py` injects an in-memory ADB callable into the actual production collector. It rejects any non-fake ADB executable or command that differs from the next frozen manifest operation. Dynamic PID values are normalized only for comparison. The model tracks the remote file, simulated parent/child process set, transfer count, executions, cleanup, and unexpected commands. It issues the PID sentinel only after both modeled processes are absent. It never calls `subprocess` or discovers a physical device.

Each successful run executes all 13 manifest commands in order: host version, one device inventory, parent metadata, initial exact ENOENT, one relative-source push, exact regular-file metadata, exact-path MD5, `--version`, one complete remote PID expression, `--self-test`, its PID expression, one exact-path `rm`, and final exact ENOENT. The test-only stock-state callback returns true. Each run returns `TEST_A_PASS_FOR_REVIEW` **inside the simulation only**. Fifty fresh consecutive runs completed: 50 transfers, 100 simulated diagnostic invocations, 50 exact cleanups, zero unexpected commands, zero modeled file leaks, zero modeled process leaks, and zero failed cycles.

The corrected process command remains one complete argument after `adb shell`; the old nested `sh -c` form is not in the production plan. Bounded distinct decimal PIDs, `/proc/$$` and `/proc/self/stat` controls, exact PID-bound sentinel, guest status marker, and host status are checked by the actual collector. An injected empty process response after the first diagnostic stopped before self-test and cleanup, leaving the modeled file for later recovery, as required.

The new R7E7G focused suite passed 67 tests. It includes 35 one-at-a-time stage-response mutations and 9 pre-ADB package mutations. The stage matrix covers host ADB/version/inventory, parent and exact destination, transfer count/source/output/timeout, remote metadata, digest, diagnostic content/lifecycle/guest status, process sentinel, cleanup, and final absence. The package matrix covers collector/manifest authorization hashes, artifact hashes/size/mode/symlink, manifest version, and command-plan alteration. Every injected case failed closed at the expected command boundary; its complete normalized argv trace matched the frozen prefix plus only the allowed exact-path cleanup suffix. Push and cleanup counts stayed at most one; no target command followed a host timeout. Separate stateful cases modeled a live process and unavailable procfs controls, both of which withheld the sentinel and stopped before self-test/cleanup. The earlier production collector fixtures add legacy Android formatting and failure-policy cases. These are bounded fixtures, not proof of every possible Android response.

## Layer B: isolated API17 transport

The R7E7F shell-construction probe was rerun with a unique owned AVD, dedicated one-device ADB server, `ADB_USB=0`, private server port, exact emulator serial, and exclusive loopback ownership checks. It passed: the old nested shell produced host rc 0 with empty output; the corrected one-expression command produced its exact sentinel; remote `$$` expanded; a live PID and a failed positive control blocked the sentinel. Private mode-0600 evidence: `build/r7e6/runs/api17-shell-construction-c7ce6acc4c1b.json`. The owned emulator/server/AVD were cleaned up. The x86 diagnostic lifecycle rerun also passed five version/self-test pairs and the fault modes; private evidence is `build/r7e6/runs/api17-runtime-d0286acc4e0e.json`, with no cleanup failures.

The emulator uses a test-only x86 binary. Its result cannot prove Honda ARMv7 loading, vehicle stock state, or Honda-specific kernel behavior. The emulator image's ownership behavior differs from the Honda and does not change the production `shell:shell` requirement.

## Recovery preparation

The separate default-disabled Phase R collector and manifest are in `tools/r7e7g_phase_r_collector.py` and `research/runtime/r7e7g-phase-r-manifest.json`. The collector verifies its source/manifest hashes and operator gates before any command. Dry run and default mode perform zero ADB calls. The offline fake tests exercise exact absence, expected regular file and MD5, wrong digest, wrong type/mode/owner/group/size/path, malformed/empty responses, wrong target, and timeout. It has no write or diagnostic-execution command. Its packet is `r7e7g-phase-r-authorization-packet.md`.

Phase C is a separate inactive proposal in `r7e7g-phase-c-conditional-cleanup-proposal.md`. The offline decision tree rehearsed absent, expected file, unexpected file, unknown process state, and a separately authorized **simulated** exact removal. Phase R's file metadata and hash do not establish current process safety. Without an independently reviewed current process-safety basis, Phase C is `NO_GO` and Test A remains blocked.

## Verification and ECC review

- Full Python suite after the first expanded matrix: 1,132 passed, 15 skipped. Three self-locator smoke tests and all configured simulator checks passed. A trailing-blank-line `git diff --check` failure in three edited Markdown files was corrected. The final matrix added exact stop/trace and timeout assertions; final configured-suite count appears below.
- Repository health: 826 Markdown files; zero broken curated links; passed.
- Artifact checker passed. Staged and canonical ARMv7 files are byte-identical; staged ELF32 ARM EABI5 PIE is 7904 bytes and mode `0555`; prior pinned API17 import audit found zero unknown imports and only `libc.so`/`libdl.so` needed.
- Independent ECC reviewer identified three baseline gaps: no full runtime argv-to-manifest comparison, fake PID sentinel without modeled process state, and Phase R insufficient by itself for Phase C. The new rehearsal and recovery decision gates address all three. The final ECC review found and prompted fixes to Phase R's imported helper hash binding, exact ordered Phase R fake argv checks, and recovery decision identity ordering. The reviewer then checked the expanded failure matrix, exact stop traces, distinct live-process/procfs model states, and timeout cases, independently reran the 67-test focused suite, and found no remaining material issue in these changes. This is an independent ECC-guided code review, not a Honda authorization or target sign-off.

## Final verification and decision

API17 x86 lifecycle: the 100-pair default run timed out at repeat 52 `--self-test` after reporting `SELF_TEST_PASS` but before its reap/status output was captured. It stopped on the 12-second host timeout, preserved ignored private evidence `build/r7e6/runs/api17-runtime-cc036acc4cab.json`, and removed the owned emulator/server/AVD with zero cleanup failures. This was a failed long rehearsal. A separate focused five-pair rerun passed (`ANDROID_API17_X86_RUNTIME_WATCHDOG_PROVEN_X86`, five completed pairs, maximum pair 2.0479 s, no cleanup failure). The earlier R7E6 100-pair pass is historical evidence, not this run's outcome. The isolated run does not prove Honda ARMv7 behavior.

Final configured offline suite: 1,136 passed, 15 skipped; 3 self-locator smoke tests; all configured simulator checks; repository health (827 Markdown files, zero broken curated links); artifact audit; and `git diff --check` passed.

Hosted verification: the first pushed implementation head `847633f663826acf9082d9f5558144c18f1af2e8` failed Offline CI because the new success tests expected the intentionally ignored ARM staging binary in GitHub's clean checkout. The tests now use the existing temporary package fixture in CI while the standalone local rehearsal remains bound to the real staged binary. On corrected implementation head `a9746582a6b425e9f47a18f889ccc386160481d9`, [Offline CI](https://github.com/bmreyes25/ClarityLink/actions/runs/38198955793) and [aggregate CodeQL with all five language jobs](https://github.com/bmreyes25/ClarityLink/actions/runs/38198955685) completed `SUCCESS`. A documentation-only report update follows; its exact-head hosted status must be checked separately.

## Offline decision and next action

`R7E7G_WET_DRESS_REHEARSAL_PASS` applies to the complete 50-cycle in-memory collector simulation and its bounded fault matrix. `API17_TRANSPORT_PASS` applies to the isolated x86 shell probe and focused five-pair diagnostic lifecycle; the separate 100-pair rerun timed out at repeat 52 and is retained as a fail-closed stress observation. `RECOVERY_PACKAGE_READY` means the default-disabled read-only Phase R package and inactive Phase C proposal are prepared for review. The imported Test A helper identity is bound to Phase R's manifest and verified before ADB use. None of these results proves Honda ARMv7 execution or current Honda state.

Next: `READY_FOR_SEPARATE_PHASE_R_AUTHORIZATION`. Real Honda file and process states, boot continuity, and stock state remain unknown; `HONDA_RECOVERY_COMPLETE` and `TEST_A_READY_FOR_AUTHORIZATION` are **not established**. Test A retry is `BLOCKED_PENDING_HONDA_RECOVERY`. No Phase R authorization, Phase C authorization, or Test A authorization was created or submitted by this milestone.

Current real Honda file state: **unknown**. Current real Honda process state: **unknown**. No Honda recovery occurred. The next physical session, if separately authorized later, is limited to Phase R inspection and review. The user does not need to return to the car for this offline milestone. Test A retry and Test B are not authorized.
