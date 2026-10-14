# ClarityLink pre-vehicle ECC audit — 2026-10-13

## Decision

**GO_FOR_PREFLIGHT_PLAN_REVIEW** — ClarityLink's offline work is sufficient to review a narrowly scoped proposal. This status does not authorize contact with the vehicle. The later review identified unresolved diagnostic-file/process state and a missing Phase S kernel/clock proof; therefore it supersedes any interpretation that this audit alone permits ADB or other Honda observations. See [Honda preflight readiness](claritylink-honda-preflight-readiness.md) for the current command-by-command proposal and gates.

**NO-GO_FOR_CONTROLLED_VEHICLE_INSTALLATION.** Do not install or enable ClarityLink in a Honda. Honda Display 1 admission, physical scanout and geometry, real warning priority, authenticated Type111 delegation, and a safe vehicle recovery/rollback path are still unproven. The candidate remains disabled. No vehicle or phone test was performed for this audit.

## Audited revision and limits

- Repository: `bmreyes25/ClarityLink`; PR #19 is open and was not merged.
- Expected baseline and exact Git HEAD at audit start and report preparation: `6cc9bc263e4e7f0974ababddc0466f5d3b0d77cd` (`docs: record final campaign check results`). It matches PR #19 head.
- PR base observed: `edea469044c1e259a43e3dd441600e95e148670a`.
- Audit checkout: detached worktree at the requested HEAD. The source/test changes described below are present but not committed: warning admission now fails closed, and its regression assertion was updated. The report is new. No PR merge or remote write occurred.
- Audited closeout: [cl-imp-14-final-closeout.md](cl-imp-14-final-closeout.md).
- The audit examined the full implementation and prior-art boundaries, reproduced host tests/demo/native conformance, rebuilt artifacts, inspected the candidate APK, and obtained an independent ECC review. Hosted CI/CodeQL records in the closeout were not rerun here.

## Evidence-backed component status

“Host” means offline implementation/model evidence. API17 emulator evidence below is the CL-IMP-12 evidence recorded in the closeout; it was not repeated in this run because the available runner uses ADB inventory and this audit honored the no-Honda-ADB restriction. ARMv7 means compile/import evidence, not target execution. No row represents Honda or authentic iPhone validation.

| # | Component | Independently checked status | Remaining real-target evidence |
|---:|---|---|---|
| 1 | Capability descriptors | Implemented; host contract tests | Accepted Type111 schema, UUID correlation, geometry |
| 2 | `/info` response | Implemented; bounded lab profiles tested | Honda/iPhone acceptance, identity, audio and HID values |
| 3 | Type110 ownership | Stock-first mock and failure/delegation tests pass | Supported Honda session handoff; Honda must retain USB/iAP2, auth, audio, Siri, calls and controls |
| 4 | Type111 setup | Contract, stale-generation and secondary-only paths tested | Actual Honda request/response and iPhone admission |
| 5 | Stream endpoints | Separate worker/listener lifecycle and reconnect tested | Endpoint/port behavior on target |
| 6 | Security context ownership | Separate fail-closed production defaults; fixture and negative tests | Production keys, cryptographic context and authenticated session |
| 7 | Screen/frame parsing | Bounded modeled Type110/Type111 parsing and malformed-input tests | Actual Type111 packetization, opcodes and timestamps |
| 8 | H.264 decoder | Genuine H.264 fixture decode reproduced on host; API17 MediaCodec path and resolution reset have emulator evidence | Authentic Type111 stream/configuration and Honda decode/performance |
| 9 | Native buffer bridge | JNI/native lifecycle and sanitizer evidence; ARMv7 library built and imports audited | Java APK does not load the `.so`; no Honda process/surface bridge |
| 10 | Android View renderer | Synthetic viewport and Canvas path tested; API17 emulator evidence | Actual cluster output, transforms, safe area and scanout |
| 11 | Presentation host | Candidate path and disabled app contract inspected; emulator admission evidence is synthetic | Honda display enumeration/admission, required signature/permissions |
| 12 | Hosted-view adapter | Project-owned API17 host and simulated Honda-style adapter tested | No supported Honda host integration |
| 13 | Frame IPC | Private bounded Binder/pipe model; UID/version/frame/lifecycle checks tested; API17 emulator evidence | Honda-side IPC permission and remote acceptance |
| 14 | Session lifecycle | Generation fencing, teardown and reconnect tested; 32 runtime cycles recorded | Honda process/display lifecycle |
| 15 | Safe-area rendering | Synthetic immutable viewport, clipping and rounding tested | Measured cluster geometry and physical coordinate mapping |
| 16 | Warning preemption | Synthetic warning preemption/resume tested; production Honda gate now rejects all caller assertions | Real warning source, z-order, priority and latency |
| 17 | Resource cleanup | Host stress/sanitizer evidence; 100 native and 32 runtime cycles recorded; API17 selected lifecycle cleanup tested | Target failure behavior and memory/resource limits |
| 18 | ARMv7 build | Rebuilt 32-bit ARM shared library; API17 symbol audit reports zero unknown imports | Execution on Honda Tegra/ARMv7 hardware; `.so` not loaded by APK |
| 19 | Test/candidate APK packaging | Rebuilt and inspected; lab APK only for emulator; candidate disabled and permission-free | No authorized vehicle install path or Honda signing evidence |
| 20 | Future diagnostic/deployment tooling | Static plans and offline models only; no vehicle diagnostics run | Target access, permissions, deployment, recovery and rollback need separate scope and evidence |

Overall software status: the requested 20 components exist to varying model/build levels, but “implemented” is not “Honda compatible.” The evidence boundary in every row remains decisive.

## Offline regression and lab reproduction

At first run, the exact baseline suite reported **1,427 passed, 15 skipped**. Investigation found one skip was the native R7B conformance executable, which the runner expects under ignored `build/r7b/`. I built it from committed synthetic fixtures using `tools/build_r7b_host.sh`; it reported `NATIVE_R7B_PASS dual_orderings=2 secondary_isolation=PASS decoded_per_sink=102 cycles=100 malformed=PASS production_security=FAIL_CLOSED resources=0`. The final complete run then matched the closeout count:

- `PYTHON=/Users/bmreyes24/ClarityLab/clarity-analysis/.venv/bin/python ./tools/run_tests.sh`: **1,428 passed, 14 skipped** (75.04 s on final reproduction).
- Standard-library self-locator smoke: **3 passed**.
- Simulator contract adapter, dual-screen model, guidance expiry and Type111 failure twin: all passed.
- `git diff --check`: passed.
- Focused API17 Java policy/lifecycle/renderer tests (`tools/test_r7c_java_api17.sh`, pinned local API17 SDK/JDK supplied): all four runners passed, including 100-cycle lifecycle cleanup. The warning policy regression now verifies that even caller-supplied `APPROVED` fields do not authorize Honda admission.
- The host dual-display demo (`demo/cl_imp_11/dual_display_lab.py`): **PASS / MODEL_ONLY**. It decoded the synthetic H.264 fixtures and reported distinct simultaneous Type110/Type111 images, warning preemption/resume, Type111 malformed-media isolation while Type110 remains active, generation reconnect, and cleanup. It explicitly reported `physicalScanout=UNPROVEN` and `hondaIntegration=DISABLED`.

### All 14 final skipped test instances

These are missing private or optional local artifacts, not vehicle test cases. The initial 15th skip was resolved by the safe host-only native build above.

| Count | Tests / skip reason | Classification |
|---:|---|---|
| 1 | `tests/honda/test_hook_boundary.py::test_elf_inspector_reads_verified_local_jmcs_when_available` — ignored forensic ELF absent | Private preserved Honda binary unavailable; cannot independently revalidate its fingerprint |
| 1 | `tests/honda/test_hook_boundary.py::test_exact_hook_group_prepare_requires_build_fp_and_all_sites_before_writes` — ignored Honda `jmcs` ELF absent | Same missing local binary; synthetic transaction tests still ran |
| 1 | `tests/offline-decoder/test_offline_decoder.py::test_two_independent_decoders_replay_entire_fixture` — optional bundled FFmpeg and 800×480 local fixture absent | Optional capacity/replay dataset absent; the portable synthetic H.264 decode and dual-display demo ran |
| 3 | `tests/preload-probe/test_probe_artifacts.py` (all three tests) — `CLARITYLINK_PROBE_DIR` and `CLARITYLINK_LLVM_READELF` not set | Synthetic ARM preload probe binaries not built/provided; no real target involved |
| 1 | `tests/tools/test_43s1_artifact_revalidation.py::test_reference_jmcs_and_thumb_bl_decode_independently` — preserved `extracted/system/system/bin/jmcs` absent | Private Honda artifact unavailable |
| 3 | `tests/tools/test_43s1_artifact_revalidation.py::test_callsite_and_frame_fingerprints_reject_modified_artifact` (three parameter offsets) — same absent ELF | Private Honda artifact unavailable |
| 4 | `tests/tools/test_jmcs_callsite_plan.py::PrivateHondaArtifactTests` (four methods) — local-only `jmcs` absent | Private binary-based plan/corruption checks unavailable; synthetic branch and malformed-input checks ran |

The four local `jmcs` groups above remain skipped by design because those private binary inputs are not committed. No Honda or firmware artifacts were fetched. All remaining skips are transparent and have concrete reasons; do not interpret them as evidence that the private Honda-binary properties were validated.

## Independent ECC assessment and remediation

An independent ECC reviewer inspected the exact-HEAD implementation and then reviewed the remediation. This was a code review, not a checklist.

1. **High — warning/display safety gate trusted caller assertions.** `WarningVisibilityPolicy.safeForHonda()` previously accepted public caller-supplied `APPROVED`, visibility, and protected-region booleans; `blankOnInterrupt` was unused. The reviewer confirmed this could not establish real warning arbitration. **Resolved safely for this candidate:** [DisplayPolicy.java](../../android/src/main/java/org/claritylink/android/DisplayPolicy.java) now returns `false` unconditionally for Honda admission until a trusted evidence source and real warning path exist. [OfflinePolicyTest.java](../../android/src/test/java/org/claritylink/android/OfflinePolicyTest.java) covers the caller-asserted approval case. The ECC reviewer approved the fix. The test-only emulator path remains gated by `layout.testOnly` and is separate from Honda admission.
2. **High design risk — ChaCha nonce uniqueness depends on key/context discipline.** `ModernChaChaScreenSecurity` resets its counter on each open and uses a zero prefix plus a counter. Reusing a key across contexts repeats nonces. No production Honda cryptography/key provider is implemented and the default Type111 security path fails closed. **Unresolved, safely not changed:** correct nonce/key behavior depends on the actual authenticated protocol and key derivation, which have no accepted Type111 evidence. Keep the feature disabled; require enforced per-stream/per-generation key derivation or proven nonce-domain separation before production use.
3. **Medium — lab authentication asserts its own authority properties.** `LabAuthenticationProvider` is a harness contract and cannot prove genuine MFi/Honda authority. Documentation disclaims that proof, and no production provider is supplied. **Unresolved by design and non-production:** do not treat lab handoff as authentication or enable it as an authority provider.

The reviewer found positive boundaries: stock delegation is explicitly a mock; production Type110/111 security defaults fail closed; generation/resource identity is checked on receive; the candidate is disabled; and API17/ARMv7 statements are scoped to emulator/build evidence rather than Honda execution.

## Security, compatibility and ownership matrix

| Area | Offline/API evidence | Honda/iPhone conclusion |
|---|---|---|
| Authentication | Unavailable Android auth adapter says not genuine; lab provider is self-asserted | No genuine authenticated iPhone Type111; no bypass was used |
| Crypto | Fixture decoding and provider boundaries tested; production defaults fail closed; nonce reuse risk exists in the optional Modern ChaCha model if a key is reused | Actual Honda/iPhone cipher, keys, nonce, KDF and per-stream context unknown |
| Type110/111 isolation | Independent mock owners/listeners, per-generation lifecycle, failure isolation and native conformance reproduced | No supported stock-session delegation or simultaneous Honda coexistence |
| Binder/IPC | Private Binder/pipe model enforces bounded frame size (4 MiB), UID/version/generation checks; no target service contract evidence | No Honda privilege/signature/IPC acceptance established |
| Memory/ownership | Explicit close paths, frame ownership, stale-generation checks, synthetic stress and native `resources=0` result | No Honda heap, decoder, surface or process-death behavior known |
| Permissions | Rebuilt candidate and lab manifests declare no `uses-permission`; candidate app, activity and service are disabled; service is non-exported | No permission-free Honda admission evidence; target signature/privilege requirements unknown |
| API17 | Java source/target 7 compile against API17; focused Java models pass; prior closeout records an isolated Android 4.2.2 x86 emulator run | No Honda API17 framework behavior established; this run did not access ADB or rerun emulator |
| ARMv7 | `armeabi-v7a`, ELF32 ARM shared object rebuilt; NDK 23.2.8568313 API17; symbol audit zero unknown imports | Compile/import audit only; no ARMv7 target runtime or Honda Tegra test |
| Displays/warnings | Synthetic 800×480 policy, Canvas and warning model; Honda-facing admission hard closed | Display 1 admission, physical safe area, scanout, warning ownership/priority and latency all unknown |
| Stock CarPlay interference | Candidate disabled, no permissions, no stock-process hooks in its manifest; host delegation is a mock. Repo also contains offline legacy hook/diagnostic plans and reversible memory models. | No interference test or installation occurred. Cannot claim an installed integration is non-interfering; no factory process/file/setting was touched |

### HondaHack-derived assumptions

The repository treats HondaHack/Xposed observations as private precedent, not as a supported public API. Prior-art notes are static evidence and include synthetic display profiles. An injected in-process View, observed type-2006 roots, or a screenshot cannot establish an independent app contract, display z-order, warning priority, safe viewport, or scanout. No HondaHack-derived assumption was promoted to target proof in this audit.

## Artifact verification and disabled candidate inspection

The documented `tools/build_cl_imp_12_artifacts.sh` rebuilt successfully with the pinned Android API17 SDK, NDK 23.2.8568313 and JDK 17. The source tree did not contain the ignored `build/r7b` parent directory assumed by the first build attempt; creating that build directory allowed the documented pipeline to complete. No source or private Honda artifact was fetched.

| Artifact | Closeout SHA-256 | Rebuilt SHA-256 | Result |
|---|---|---|---|
| ARMv7 `libclaritylink_android.armv7.so` | `ebba888796584d583493194155a0f997e6ac279f5da89e1271ac4030509d19c9` | same | Exact match; ELF32 ARM; zero unknown imports |
| `claritylink-android-api17.jar` | `d4fe4d5840ad9dd5d14670a17337425b71ebf5e92f1a329a95d5885c28def677` | `36c432d5e515f707106a86b883e66be2724950377e999f342e33151b72896e12` | Expected difference: contains the ECC-reviewed fail-closed policy change |
| `claritylink-display-lab.apk` | `b8cbe434c053529f475f9a7be2a3122d1a8dc6bbd7a3a0c9b3c4d96704282e63` | `21215fedddd0201fc4d6c44ab2bd7a8076300334c175d15b281af8409079ecd7` | Expected source fix and fresh local signing key |
| `claritylink-disabled-candidate.apk` | `3b702a19adf6f58a3818813fcaa7e4f445dafbc7f9b6ed6cae8d45c8f4d4599` | `30dfb5893c3f95b327b9cdc74065507025ca356d628ef52c425fcfa3ad23b19f` | Expected source fix and fresh local signing key; still disabled |
| `api17-symbol-audit.json` | `9ac23d691c35c5074a875a04bd00b9ef4bb93bcd49c71e14cdadbd1106a6cf94` | same | Exact match |

The local signing key is ignored and absent in this fresh worktree. The rebuilt APKs verify with one RSA-2048 signer (`CN=ClarityLink CL-IMP-03 Offline Lab`, certificate SHA-256 `105855d5952f13d713b76cc93090171a4f487fed12ad2aa3fa5579a2bb1c113f`); v1/JAR signing verifies, v2/v3/v3.1/v4 are absent. As the build script specifies, repeat APK hashes require the same local signing key. The candidate APK declares no permissions; `aapt` confirms application `enabled=false`, activity `enabled=false, exported=false`, and service `enabled=false, exported=false`. This is not an install authorization. The lab APK is emulator-only.

## Factory CarPlay impact assessment

No Honda ADB, Honda install, vehicle modification, physical iPhone session, stock-process injection, authentication bypass, USB/network capture, or automatic vehicle test was performed. The candidate remains disabled. Its no-permission manifest and separate process boundary reduce what this artifact can do if accidentally considered, but do not prove an enabled vehicle deployment would preserve stock behavior. The broader repository contains historical interposer/hook and diagnostic planning code; those paths are not part of the disabled candidate and were not executed. Any future live hook, privileged access, stock binary change, or undocumented bridge is a separate stop-and-review decision.

## Phase S, Phase C, diagnostic recovery, rollback

- Phase S and Phase C remain separately scoped Honda operations; the closeout explicitly requires fresh authorization for any such work. Neither is authorized or executed here.
- `NEXT_ACTION.md` records the prior Test A executable transfer and `--version` invocation without confirmed process absence/cleanup. Current remote file/process state is **unknown**. It directs a separately authorized read-only Phase R inspection before conditional Phase C cleanup; Phase R alone cannot prove process safety. Test A retry and Test B are not authorized. No Honda diagnostic action was taken during this audit.
- There is no Honda-ready enabled APK, proven install/disable procedure, verified pre-change snapshot, recovery owner, or on-Honda rollback command. Host mock rollback/retry tests are not vehicle restoration evidence. Installation remains blocked until exact artifact/config hashes, operator stop path, reinstall/recovery source, and exact-state restoration are supported and separately validated.

## Exact next recommended test

Plan—but do not execute without separate explicit authorization—a **read-only vehicle identity/display preflight**. In a parked vehicle, with no phone connected and no external device, have the authorized operator record only the head-unit/cluster model and software version from the normal built-in About screen or owner documentation, plus any documented Display 1 topology. Do not enter service menus, change settings, connect ADB, install anything, reboot, access processes/files, capture traffic, or invoke a diagnostic executable. Stop if the information is not available through ordinary user-facing documentation/UI. This can select the right compatibility target; it cannot prove admission, warning priority, Type111 authentication/delegation, scanout, or rollback.

Before any installation proposal, separately obtain evidence for: genuine authorized Type111 source and protocol; supported stock-preserving Type110 delegation; independent-app Display 1 admission and permissions; measured physical geometry and warning arbitration; representative-hardware reliability; and a proven operator-controlled restoration path. If any depends on root, a stock-process hook, stock binary modification, or unknown cleanup semantics, stop for a separate design/safety decision.

## Formal assessment

- **GO_FOR_PREFLIGHT_PLAN_REVIEW:** planning only; no vehicle action is authorized.
- **GO_FOR_SEPARATELY_AUTHORIZED_READ_ONLY_PREFLIGHT:** limited to the single operator-facing identity observation described in the readiness report, after its own exact authorization; ADB is not included.
- **NO_GO_UNRESOLVED_RECOVERY:** Phase S, Phase C, Test A, cleanup, process inspection, and any ADB observation remain blocked pending the gates in the readiness report.
- **NO_GO_UNRESOLVED_SECURITY:** Type111/authentication/session/delegation and any renderer or installation test remain blocked by absent production trust and interface evidence.
- **GO_FOR_CONTROLLED_VEHICLE_INSTALLATION:** **NO-GO**. Display admission, warning priority, authenticated Type111 delegation, and safe recovery remain unproven; these are explicit hard gates.
- **Answer to the final objective:** ClarityLink is sufficiently validated to start planning its first authorized read-only Honda compatibility preflight. It is not sufficiently validated for any controlled installation or for presenting the dual-display implementation as Honda-compatible.
