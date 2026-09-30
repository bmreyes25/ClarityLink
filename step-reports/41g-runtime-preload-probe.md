# Step 41G — Runtime preload compatibility probe build

**Outcome: synthetic API 17 ARMv7 probe source and binaries built/validated offline; ARM runtime execution unavailable.** This continues from actual repository HEAD `b53a3b0` (which includes the previous Step 41G lab decision), rather than resetting the branch to the older prompt base `aa756f6`.

No vehicle, ADB, staging, jmcs load, boot/recovery/partition change, or Type111 live work occurred. No Honda binary was executed. Generated probe binaries were written to `/tmp`, checked, hashed, and deleted; no generated binary is tracked.

## Probe definition

- Main executable: `src/claritylink-probes/preload/probe_exec.c`; writes `CLARITYLINK_PROBE_MAIN_RAN` and exits 42.
- Shared library: `src/claritylink-probes/preload/probe_preload.c`; constructor writes `CLARITYLINK_PROBE_CONSTRUCTOR_RAN` and returns normally.
- Both use only libc `write`; no Honda APIs, network, CAN, display, or persistent file writes.
- Build driver `build_probe.sh` uses a caller-supplied local NDK r23c and an output directory outside the repository. It targets ARMv7/API 17 and does not execute outputs.
- Static artifact checks are in `tests/preload-probe/test_probe_artifacts.py`.

The local NDK r23c DMG was mounted read-only, using Android clang 12.0.9, target `armv7a-linux-androideabi17`. The executable verified as ELF32 ARM EABI5 PIE, dynamically linked with interpreter `/system/bin/linker`, and `libc.so` dependency. The preload verified as ELF32 ARM EABI5 `ET_DYN`, SONAME `libclaritylink_preload_probe.so`, and `libc.so` dependency. Three artifact validation tests passed. Temp artifact hashes and the future test plan are in [runtime preload probe](../research/deployment/runtime-preload-probe.md). The read-only NDK image was detached after the build.

No QEMU user-mode runner/container/ARM guest is available, so no local ARM execution occurred. Local results for constructor execution, absolute-path handling, separator handling, or missing-preload failure remain **UNKNOWN**. The future parked probe plan is ready for a separately scoped/authorized milestone; it tests a standalone probe process and does not establish jmcs's SELinux domain or `AT_SECURE` state.

## Parallel offline Type111 status

All requested model layers already exist: Setup augmentation/transaction, Type111 lifecycle/security model, 128-byte ScreenStream framing, stateful CTR model, VideoConfig parser, H.264 length-prefix-to-Annex-B conversion, and renderer handoff mock/API17 skeleton. Focused verification passed: negotiation 18, transport 29, display/session model 12, renderer 8; the host-only Display B end-to-end smoke passed. These models do not validate Honda Type111 wire acceptance. Descriptor correlation, exact Type111 response fields, Type111 KDF/key reuse, and physical ExternalDisplay decoder handoff remain unknown or prior-art-derived. Details: [offline Type111 pipeline status](../research/carplay/type111-offline-pipeline-status.md).

## Decision gate

```text
PROBE ARTIFACTS BUILD: YES
LOCAL PROBE EXECUTION: NOT AVAILABLE
ABSOLUTE LD_PRELOAD LOCALLY: UNKNOWN
MISSING PRELOAD FATAL LOCALLY: UNKNOWN
FUTURE PARKED PROBE READY: YES (design/build only; separate authorization; never targets jmcs)
JMCS NO-OP LOAD TEST: NOT READY
TYPE111 LIVE WORK: NOT READY
BIGGEST BLOCKER: Honda runtime/linker and jmcs-specific security/mapping behavior have not been exercised; local ARM execution is unavailable
```

## Validation

- `sh -n src/claritylink-probes/preload/build_probe.sh`: passed.
- Probe artifact validation: 3 passed with `CLARITYLINK_PROBE_DIR` and `CLARITYLINK_LLVM_READELF` set to the temporary build output and NDK `llvm-readelf`.
- Setup/negotiation (`python3 -m unittest discover -s tests/negotiation -v`): 18 passed.
- ScreenStream/crypto/VideoConfig/H.264 receiver (`python3 -m unittest discover -s tests/transport -v`): 29 passed.
- Display/session (`python3 -m unittest discover -s tests/carplay-session-model -v`): 12 passed.
- Renderer (`python3 -m unittest discover -s src/claritylink-renderer/tests -v`): 8 passed.
- Host-only Display B integration smoke: passed when invoked directly. `unittest discover` finds no unittest cases in that pytest-style integration module; pytest is not installed, so no package was installed.
- `git diff --check`: passed before commit.
