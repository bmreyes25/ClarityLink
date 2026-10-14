# R7E6 — API17 runtime validation and Test A readiness

Date: 2026-10-11  
Branch: `architecture/r7e-parked-car-compatibility-preparation`  
Starting HEAD: `34f4f91cc7950235902e3b4f1ef16724634b74d4`
R7E6 implementation checkpoint: `cd1d47b51f84e7f0c79a28f079f620fcd4ee0631`

## Decision

`R7E_TEST_A_EXECUTION_PACKAGE_READY`. The next step is `READY_FOR_EXPLICIT_TEST_A_AUTHORIZATION`. Test A remains `NOT_EXECUTED` and `NOT_AUTHORIZED`; R7E6 did not operate the Honda.

## Runtime proof

The unique project-owned API17 x86 AVD reported Android 4.2.2, API17, x86, and Dalvik 1.6.0. Emulator ADB was confined to an exact serial and dedicated server port, USB discovery was disabled on that server, and host socket checks confirmed only the owned server/emulator on the target port. The private evidence record is ignored under `build/r7e6/runs/api17-runtime-69ad6acbcd28.json` (SHA-256 `297e1dd98b93947a7e1595a7d48474c56f618f9f6ed544305ec7f8d84bf3a71c`).

The runtime matrix passed: `--version`, `--self-test`, child busy-loop and sleep deadlines, child crash mapping, ignored `SIGCHLD` reset, injected fork failure, waitpid-error exact recovery, and parent watchdog exact child termination. It completed 100/100 version/self-test pairs. Exact PIDs were observed from the supervisor and confirmed absent; exact staged-file metadata/digest checks, exact removal/final absence, and emulator cleanup passed. No physical Android or Honda target was contacted.

## Frozen target artifact and package

- ARMv7/API17 artifact: 7,904 bytes; SHA-256 `9e20d1ad715be6c9974f9a89e1aa310283bc128f87350fb05cb224b8e247c063`; MD5 `6137a693a77646aaf9a4cf0f351731d4`.
- ELF: ELF32 little-endian ARM EABI5 PIE; `DT_NEEDED`: `libdl.so`, `libc.so`; pinned API17 imports all resolve.
- Staging: byte-identical, mode `0555`; expected Honda remote mode `0555`, owner/group `shell:shell`; no target `chmod`.
- Collector: `tools/r7e6_test_a_collector.py`, SHA-256 `5837624209be870b60027041235428e5839dcf4b85055bbdfd83cd759794235e`; default `NOT_AUTHORIZED`; dry run zero ADB operations.
- Fake-ADB fixtures: 23 passed.
- Manifest: `research/runtime/r7e6-test-a-plan-manifest.json`, SHA-256 `86f270be05e166e2a54738e186a350fcd3d9f5f8f8b804de4b668b18ffdc7205`.
- Authorization packet: `research/runtime/r7e6-test-a-authorization-packet.md`; it explicitly says Test A is not authorized and the execute flag is not authorization.

## ECC and verification

ECC C++ testing/security guidance was applied throughout architecture and failure review. Manual reviews covered process ownership/PID reuse, signal-handler safety, API17 imports, artifact capabilities, ADB isolation, exact cleanup, collector gates, and authorization separation. An independent ECC review service was unavailable, so no external ECC sign-off is claimed.

Verification: focused watchdog and collector checks passed (32 tests); the full suite passed (1,005 passed, 15 skipped); self-locator passed (3 tests); configured simulator checks passed; repository health passed (815 Markdown files, zero broken curated links, zero forbidden extensions); artifact checker and pinned API17 import audit passed with zero unknown imports; `git diff --check` passed. Hosted Offline CI and CodeQL must still pass on the exact final pushed head.

## Safety boundaries

Honda commands: zero. Physical Android contacted: no. Test A executed: no. Test A authorized: no. Test B auto-started: no. Display1, Presentation, CarPlay, MFi, iAP2, USB ownership, root, and jmcs changes remain excluded.
