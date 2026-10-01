# Step 43N — offline trampoline model and external Type111 oracle evidence

| Evidence item | Source | Finding / classification |
|---|---|---|
| Honda callsite and ABI frame | `extracted/system/system/bin/jmcs`, SHA-256 `cbc7ba881648fb8ffdfcc4c1100a028345c37134a2ae3b9dff7d76572851c232`; LLVM Thumb disassembly; `tools/jmcs_integration/callsite_plan.py` | `HONDA_CONFIRMED`: `0x28afba` bytes `fe f7 d1 ff`, direct BL to `0x289f60`, continuation `0x28afbe`, saved LR `0x28afbf`; 0x2d8 frame delta keeps callsite SP aligned assuming AAPCS entry alignment. Planner gates hash, instruction, surrounding context, and caller prologue. |
| Trampoline control-flow contract | `src/claritylink-negotiation/trampoline_contract.py`; `tests/negotiation/test_trampoline_contract.py` | `OFFLINE_PROJECT_IMPLEMENTATION` / `SYNTHETIC_TEST_VALUE`: caller LR saved/restored, original args passed, stock call once, serializer result/statusOut preserved; no patch bytes or code emitted. |
| DiPlay Type111 behavior | pinned commit `f2d06951b4e8114dbb62f551c12a32a845a3042f`; [DiPlay differential](research/carplay/diplay-type111-differential.md) | `EXTERNAL_PRIOR_ART`: second display 111, URLs, view areas, enabled features, own dataPort, UUID-scoped UI/keyframe controls, modern DataStream crypto. Pinned docs report a physical iOS 27 cluster test: `EXTERNAL_PHYSICAL_VALIDATION`. None is Honda fact. |
| PlayPort protocol/oracle | pinned commit `9a0882dd0ffe48e467b59d58b12d81391df55ade`; [PlayPort differential](research/carplay/playport-type111-differential.md); [lab plan](research/lab/playport-type111-oracle-plan.md) | `EXTERNAL_PRIOR_ART`: protocol supports 110/111 and preserves type through media and web wire; default server has no cluster and current browser UI has one canvas. Oracle is design only; no phone test. |
| Security boundary | [Honda vs modern security](research/carplay/honda-vs-modern-type111-security.md); `research/carplay/honda-screen-crypto.md` | Honda Type110 AES-CTR is `HONDA_CONFIRMED`; DiPlay/PlayPort DataStream HKDF + ChaCha20-Poly1305 is `EXTERNAL_PRIOR_ART`; Honda Type111 crypto remains `HONDA_UNKNOWN`. |
| Readiness | [Step 43N report](step-reports/43n-trampoline-and-type111-oracle.md); `PROJECT_STATE.md`; `NEXT_ACTION.md` | Trampoline contract ready offline, attachment designed not deployed; Type111 model has stronger external evidence; Honda live and Type111 live remain NOT READY; LD_PRELOAD PARKED. |

# Step 43M — existing-call wrapper seam (offline)

| Evidence item | Source | Finding / classification |
|---|---|---|
| Reference identity and Setup success path | `extracted/system/system/bin/jmcs`, SHA-256 `cbc7ba881648fb8ffdfcc4c1100a028345c37134a2ae3b9dff7d76572851c232`; `research/carplay/honda-post-setup-existing-call-map.md` | `HONDA_CONFIRMED`: Setup BL `0x28af72`; serializer BL `0x28afba`; request/response/session remain in caller frame; response released before HTTP send. |
| Existing function linkage | `research/carplay/honda-wrapper-linkage-audit.md` | `HONDA_CONFIRMED`: bounded calls are internal direct BLs, no relevant PLT/JUMP_SLOT route found; runtime-loader precedence is not inferred. |
| Serializer wrapper contract | `research/carplay/honda-request-send-plist-wrapper-audit.md`; `src/claritylink-negotiation/wrapper_contract.py` | Honda ABI/result is static evidence; transaction state, fail-open/rollback, and preservation checks are `OFFLINE_PROJECT_IMPLEMENTATION` / `SYNTHETIC_TEST_VALUE`. Success is `r0==0xc8 && statusOut==0`. |
| Narrow future attachment target | `research/carplay/honda-minimal-future-trampoline-target.md`; `tools/jmcs_integration/callsite_plan.py` | `HONDA_CONFIRMED` target bytes/Thumb BL and static branch facts; trampoline behavior is plan-only, no patch bytes emitted, installation `HONDA_UNKNOWN`. |
| Decision/readiness | [Step 43M report](step-reports/43m-existing-call-wrapper-seam.md); `PROJECT_STATE.md`; `NEXT_ACTION.md` | Existing function wrapper not supported; strategy C, minimal validated trampoline design next. JMCS implementation/live/Type111/ExternalDisplay remain NOT READY; LD_PRELOAD PARKED. |

# Step 43H — HTTP commit and receiver-session cleanup (offline)

| Evidence item | Source | Finding / classification |
|---|---|---|
| Preserved Step 43G / binary identity | Step 43G files; jmcs SHA-256 `cbc7ba881648fb8ffdfcc4c1100a028345c37134a2ae3b9dff7d76572851c232` | Step 43G uncommitted artifacts were preserved; reference hash matches. |
| HTTP response commit return | `HTTPConnectionSendResponse` `0x29dbe4`; `HTTPHeader_Commit` `0x29dd18`; `_connectionHandleMessage` call `0x28b790` | `HONDA_CONFIRMED`: commit error is returned unchanged, handler returns it, state machine checks it and takes connection stop/close callback. |
| Response send state machine | `_HTTPConnectionRunStateMachine` `0x29d698`; `SocketWriteData` `0x2a01c0`; `UpdateIOVec` `0x29fc94` | `HONDA_CONFIRMED`: state 0 read/handler, state 1 write; EINTR retries, EAGAIN/partial writes return 11, terminal results close. |
| Finalizer/session teardown | `_connectionFinalize` `0x289d90`; `AirPlayReceiverSessionTearDown` `0x2852ec` | `HONDA_CONFIRMED`, conditional on private context session pointer: finalizer calls teardown, then releases/clears session reference. |
| Teardown order | `_ScreenTearDown` `0x284628`; `_TearDownStream` `0x284bd8`; Step 43H report | `HONDA_CONFIRMED` for bounded sequence; accepted ScreenStream socket lifetime and crypto zeroization unknown. |
| Project child lifecycle | `research/carplay/honda-project-child-lifecycle-contract.md`; synthetic failure tests | `HYPOTHESIS`/`SYNTHETIC_TEST_VALUE`: exact-once project cleanup contract tested; supported Honda attachment point remains unknown. |
| Tests / readiness | Step 43H report; `NEXT_ACTION.md` | Canonical offline checks pass; project cleanup and seam remain `NEEDS_MORE_STATIC_PROOF`; live gates closed. |

# Step 43G — Setup CF ownership and connection failure cleanup (offline)

| Evidence item | Source | Finding / classification |
|---|---|---|
| Artifact / address mapping | `extracted/system/system/bin/jmcs` SHA-256 `cbc7ba881648fb8ffdfcc4c1100a028345c37134a2ae3b9dff7d76572851c232`; `tools/elf_va_map.py`; `research/carplay/honda-setup-cf-callbacks.md` | `HONDA_CONFIRMED`: exact reference hash; PT_LOAD-aware VA/file map plus GOT relocations resolve constructor arguments and callback table words. |
| Setup response dictionary | `AirPlayReceiverSessionSetup` `0x28557e`; detailed callback report | `HONDA_CONFIRMED`: key table `0x3428fc`, value table `0x342914`; wrappers dispatch to CFL retain/release/equality/hash. Both are CFType-style retaining tables. |
| streams array | `_AddResponseStream` `0x284de2`; detailed callback report | `HONDA_CONFIRMED`: table `0x342858` with retain/release/equality and NULL description; retaining CFL callbacks. |
| Type110 ownership | `research/carplay/honda-type110-ownership-ledger.md` | `HONDA_CONFIRMED`: entry retained by array, streams array retained by response, local references released after insertion; recursive finalizer path identified. Per-scalar temporary counts/aliases are not all quantified. |
| Serialization boundary | `research/carplay/honda-post-setup-caller-liveness.md`; Step 43G report | `HONDA_CONFIRMED`: synchronous serialization precedes caller response release; subsequent HTTP/network delivery does not need CF graph rollback. |
| HTTP and session failure | `research/carplay/honda-http-failure-session-cleanup.md` | Terminal read/write error closes HTTP connection and connection finalizer invokes receiver session teardown; commit/queue failure effect remains `UNKNOWN`; project-child subscription not established. |
| Synthetic model / readiness | `src/claritylink-negotiation/response_delivery_model.py`; `tests/negotiation/test_response_delivery_ownership.py`; Step 43G report | Synthetic lifecycle invariants only; no Honda semantics inferred. Seam needs more static proof; all live/implementation gates remain closed; LD_PRELOAD parked. |

# Step 43D — Honda Setup stream identity (offline)

| Evidence item | Source | Finding / classification |
|---|---|---|
| Exact Setup callback arguments | `research/native/jmcs/focused-annotated.txt`; Step 43H report | Setup response dictionary and `streams` callback pointers remain unresolved. Named tables alone are not call-site proof. |
| Positive call-site controls | Same disassembly | `/info` dictionary at `0x287af8` passes named CFType key/value tables; global screen array at `0x2a18ae` passes named CFType array table. These are separate objects. |
| Type110 ownership | `research/carplay/honda-cf-callback-ownership.md` | Entry retain/release ledger and response-to-streams retaining edge remain unknown/partial. |
| Serialization boundary | `research/carplay/honda-post-setup-caller-liveness.md` | Response graph is released after synchronous serialization; later network failure does not need CF graph rollback. Project stream cleanup edge is unknown. |
| Readiness / next | [Step 43H report](step-reports/43h-cf-callback-fingerprint.md); `NEXT_ACTION.md` | `NEEDS_MORE_STATIC_PROOF`; all implementation/live gates NO; LD_PRELOAD PARKED. Next: recover exact Setup callback arguments and session cleanup callback. |


| Evidence item | Source | Finding / classification |
|---|---|---|
| Type-110 request fields | `research/carplay/honda-setup-stream-identity.md`; hash-matched `jmcs` SHA-256 `cbc7ba881648fb8ffdfcc4c1100a028345c37134a2ae3b9dff7d76572851c232` | `HONDA_CONFIRMED`: Setup iterates `streams[]`, reads `type`; Type 110 reads a nonzero uint64 `streamConnectionID` and passes it with receiver-session master material to screen crypto derivation. Other candidate keys remain unrecovered. |
| Type-110 response | Same report; `0x286124`, `0x28614a–0x286168`; `_AddResponseStream` `0x284db8` | `HONDA_CONFIRMED`: listener port selected from requested port 0 becomes `dataPort`; response stream entry inserts constant `type=110`; no streamConnectionID echo observed in that entry. |
| Type 111 stock behavior | `research/carplay/honda-mixed-stream-setup.md`; Step 43D report | `HONDA_CONFIRMED`: unsupported type is logged/skipped without a stock Type-111 response entry; this says nothing about iPhone selection. |
| UUID correlation | `research/carplay/honda-display-uuid-flow.md`; Setup trace | `/info` numeric Screen UUID is inserted via a separate path. No direct UUID-to-streamConnectionID link found in inspected dataflow; UUID semantic role remains `HONDA_UNKNOWN`. |
| Prior art | `research/carplay/setup-stream-identity-prior-art.md` | `APPLE_PUBLIC_ARCHITECTURE`: Apple WWDC19 multi-H.264 cluster streams. `EXTERNAL_PRIOR_ART`: carlink_linux pinned `fbbfa59400dac4704f34a5d76e745080ce7d6338`; MHI2 pinned `c2f811f1a5c84dae3a62f4cf9b4a9e65fc3f7b3c`; CPC200 pinned `e3e5d005552d3fa6f264634b377d30b0794dd1eb`. None proves Honda Type111. |
| Readiness / next | Step 43D report; `NEXT_ACTION.md` | Type111 response shape, Honda display selection/binding, jmcs seam, and real renderer remain unresolved; all live gates remain NO; LD_PRELOAD PARKED. Step 43E now classifies the seam as a static candidate; next: prove instruction liveness and CF/runtime cleanup through serialization. |

# Step 43C — Honda ForceKeyFrame semantics (offline)

| Evidence item | Source | Finding / classification |
|---|---|---|
| ELF and debug entry | `extracted/system/system/bin/jmcs`, SHA-256 `cbc7ba881648fb8ffdfcc4c1100a028345c37134a2ae3b9dff7d76572851c232`; preserved `research/native/jmcs` symbol/disassembly/string reports | `HONDA_CONFIRMED`: matching ELF has debug information. DWARF names `AirPlayReceiverSessionForceKeyFrame` and gives parameter names, but low PC is zero and no usable body/address is present in saved maps. |
| Key literals and xrefs | `research/carplay/honda-forcekeyframe-semantics.md` | `forceKeyFrame` / `forceKeyFrameNeeded` strings exist; resolved readers/writers and object ownership were not recovered. Semantics remain `HONDA_UNKNOWN`; string presence is not a functional trace. |
| ScreenStream opcode scope | `research/carplay/honda-screen-framing.md`; Step 43C report | `HONDA_CONFIRMED` for recovered parser only: discriminator 3 takes its unrecognized path in `AirPlayReceiverSessionScreen_ProcessFrames`. It does not establish all Honda keyframe behavior. |
| Type111 and readiness | [Step 43C report](step-reports/43c-forcekeyframe-semantics.md); `NEXT_ACTION.md` | No Type111/control-plane/decoder-recovery meaning established; Type111, live test, jmcs integration, ExternalDisplay live render remain NOT READY; LD_PRELOAD PARKED. Step 43D supersedes its next action. |

# Step 43B — Honda Screen property sources and descriptor xrefs

| Evidence item | Source | Finding / classification |
|---|---|---|
| ELF identity and debug data | `extracted/system/system/bin/jmcs`; SHA-256 `cbc7ba881648fb8ffdfcc4c1100a028345c37134a2ae3b9dff7d76572851c232`; `research/native/jmcs/{symbols.json,disassembly.txt,focused-annotated.txt}` | Exact matching Honda binary; ARM32 ELF with symbols and DWARF. Offline static evidence only. |
| Descriptor/object path | `research/carplay/honda-copy-displays-info.md`; `research/carplay/honda-screencopymain-property-sources.md`; function `0x287ae0` and `ScreenCopyMain` `0x2a17fc` | `HONDA_CONFIRMED`: one descriptor copies eight properties from first registered Screen; fallback creates/registers main Screen. Geometry/FPS derive from configuration-backed globals. |
| UUID and stream binding | `research/carplay/honda-display-uuid-flow.md`; Type110 Setup/KDF reports | Numeric UUID insertion confirmed; generated/default source only candidate. UUID-to-stream binding not found in analyzed flow; semantics remain unknown. |
| Parallel descriptor and role | Step 43B report; `honda-server-info.md` | Mutable collection can hold more entries structurally; Honda producer appends once. No alternate builder found in audited call path; binary-wide structural conclusion remains inconclusive. No role/type insertion recovered. |
| Force-keyframe | strings at `0x337352`, `0x33737b`, `0x3379fb`; DWARF source name `AirPlayReceiverSessionForceKeyFrame` | `HONDA_UNKNOWN`: full function body/callers and Type111 relation were not recovered. Do not treat as cluster semantics. |
| Readiness / next | `step-reports/43b-screencopymain-property-source-trace.md`; `NEXT_ACTION.md` | Descriptor feasibility is only structural; Type111, live test, jmcs integration, ExternalDisplay rendering remain NOT READY; LD_PRELOAD PARKED. Step 43C supersedes its ForceKeyFrame next action; current task is Setup `type` / `streamConnectionID` versus display UUID/Screen identity. |

# Step 43A — Honda `/info` Type111 differential (2026-09-30)

| Evidence item | Source | Finding / classification |
|---|---|---|
| xcertplay descriptor builder | [Pinned commit `de9647f4bdfb1be356bed4cac0519400473712a6`](https://github.com/shilapi/xcertplay/commit/de9647f4bdfb1be356bed4cac0519400473712a6); [`AirPlayInfoPlist.kt`](https://github.com/shilapi/xcertplay/blob/de9647f4bdfb1be356bed4cac0519400473712a6/shared/src/main/java/com/shilapi/xcertplay/airplay/AirPlayInfoPlist.kt), lines 24–72, 141–189 | `EXTERNAL_PRIOR_ART`: configured type 110 main + conditional type 111 cluster with distinct configured UUID; shared fields include geometry, features, input device, viewAreas, initialViewArea, optional initialURL, and nested safeArea. Does not establish Honda requirements. |
| Honda `/info` object path | `step-reports/32-airplay-info-phone-path.md`; matching `jmcs` SHA-256 `cbc7ba881648fb8ffdfcc4c1100a028345c37134a2ae3b9dff7d76572851c232` | `HONDA_CONFIRMED`: `/info` -> `_requestProcessInfo` -> `AirPlayCopyServerInfo` -> plist serializer -> HTTP/SocketWriteData/writev static flow; `displays` is phone-facing in code. No live phone transaction observed. |
| Honda display descriptor | `research/carplay/honda-copy-displays-info.md`, function `AirPlayReceiverSessionScreen_CopyDisplaysInfo` `0x287ae0`; `research/carplay/honda-display-uuid-flow.md` | `HONDA_CONFIRMED`: one `ScreenCopyMain()` descriptor with `edid`, `features`, `maxFPS`, pixel/physical dimensions, numeric `uuid`; exact values/semantics partly unknown. No Type111 descriptor recovered. |
| Differential and literal scope | `research/carplay/honda-info-type111-differential.md`; `step-reports/43a-honda-info-type111-differential.md` | `type` is `HONDA_INDIRECT_CANDIDATE` only (Honda uses it in Setup stream dictionaries, not a confirmed display role). `primaryInputDevice`, `viewAreas`, `initialViewArea`, `initialURL`, and `safeArea` are `HONDA_ABSENT_LITERAL` in the inspected scope. `forceKeyFrame` is an indirect candidate with no second-display semantics proven. Literal absence is not semantic absence. |
| Readiness | `PROJECT_STATE.md`; `NEXT_ACTION.md` | No Type111 requirement, security, display-to-stream correlation, jmcs seam, or ExternalDisplay live path was proven. Implementation/live gates remain closed; LD_PRELOAD remains parked. |

# Step 42F — visual offline cluster demo (2026-09-30)

| Area | Primary evidence | Finding |
|---|---|---|
| Visual page | `demo/type111/index.html`; `demo/type111/README.md` | Static, dependency-light two-display mock with Strict Honda and Hypothetical Type111 views; no capture assets |
| Replay data | `src/claritylink-sim/export_visual_demo.py`; `demo/type111/replay-data.json` | Generated from both Step 42E replay modes; contains state/timeline summary only, no media bytes or keys |
| Evidence / unknowns | `research/simulator/visual-cluster-demo.md`; `tests/integration/test_visual_cluster_demo.py` | Honda, MHI2 hypothesis, synthetic values, and unknown behavior have visible separate labels; live gates remain closed |
| Preview / readiness | `step-reports/42f-visual-offline-cluster-demo.md`; `NEXT_ACTION.md` | Local browser preview checked both modes; visual demo ready, jmcs no-op/ExternalDisplay live/Type111 live NOT READY |

## Step 42E — synthetic Type111 end-to-end replay (2026-09-30)

| Area | Primary evidence | Finding |
|---|---|---|
| Capability gate and modes | `src/claritylink-sim/capability_gating.py`; `research/simulator/capability-gating-model.md` | Strict Honda mode skips Type111; hypothetical mode requires all synthetic prerequisites and explicit unknowns |
| Canonical replay | `src/claritylink-sim/synthetic_type111_replay.py`; `tests/integration/test_synthetic_type111_replay.py` | Stock delegate first; candidate setup, fake listener, config/frame parsing, Annex-B extraction, synthetic frame source, Display 1 mock and teardown are composed offline |
| Evidence and output | `research/simulator/synthetic-type111-replay.md`; `research/simulator/event-timeline-model.md` | MHI2 response profile remains hypothesis; IDs/ports/bytes/frame are synthetic; display correlation, Type111 crypto, overlay/crop remain unknown |
| Preservation/readiness | `research/architecture/type110-invariants.md`; `step-reports/42e-synthetic-type111-end-to-end-replay.md`; `NEXT_ACTION.md` | Type110 request/response and synthetic audio survive Type111 teardown; full teardown clears model state; no live gate advanced |

## Step 42D — failure-injected Type111 digital twin (2026-09-30)

| Area | Primary evidence | Finding |
|---|---|---|
| Failure matrix | research/simulator/type111-failure-matrix.md | Setup, listener, crypto/parser/config, H.264, renderer, session and reconnect failures have explicit synthetic expected behavior |
| Isolation model/test | src/claritylink-sim/type111-failure-twin.js; tests/sim/test_type111_failure_twin.js | Type110 response/stream/crypto and synthetic audio are separate from Type111 state; candidate failures and teardown are injected |
| Audio/timeline | research/simulator/audio-state-model.md; research/simulator/event-timeline-model.md | Audio isolation is synthetic invariant-only; event timeline is semantic, bounded in-memory, not Honda logs |
| Updated contracts | research/simulator/digital-twin-contract.md; research/architecture/type110-invariants.md; Type111 lifecycle/renderer notes | Failure behavior is modeled; Honda Type111 and live rendering remain unknown |
| Readiness | step-reports/42d-failure-injected-type111-digital-twin.md; NEXT_ACTION.md | Synthetic Type111 lifecycle demo ready; no live gate advanced |

## Step 42C — offline jmcs integration contract (2026-09-30)

| Area | Primary evidence | Finding |
|---|---|---|
| Type110 invariants | research/architecture/type110-invariants.md; Honda screen crypto and stream schema | Stock Setup, Type110 port/ID/KDF and receiver remain Honda-owned; synthetic tests preserve response semantics |
| jmcs inputs/outputs | research/architecture/jmcs-integration-contract.md; research/architecture/type111-integration-contract.md | Setup/session is inside jmcs; no reviewed outside-JMCS session/security/frame transfer; Type111 fields remain unknown/hypothesis |
| Unknowns/lifecycle | research/carplay/type111-unknown-register.md; research/carplay/type111-listener-lifecycle.md | Wire/security/correlation/teardown unknowns explicit; offline lifecycle is a candidate model |
| Security/renderer | research/carplay/type111-security-access-matrix.md; research/display/type111-renderer-handoff-contract.md | Independent crypto state is a design rule; no Honda Type111 KDF or supported frame API |
| Digital twin | research/simulator/digital-twin-contract.md | Profiles separate Honda evidence, MHI2 hypotheses, synthetic values and unknowns |
| Decision/readiness | step-reports/42c-jmcs-integration-contract.md; NEXT_ACTION.md | Contract defined, Type111-specific portions partial; active work offline, live gates not ready |

## Step 42B — architecture decision (2026-09-30)

| Area | Primary evidence | Finding |
|---|---|---|
| Architecture comparison | `research/architecture/type111-architecture-options.md`, `research/architecture/type111-active-architecture.md` | Target architecture is jmcs control/session integration plus ExternalDisplay-host renderer adapter; current executable work remains the digital twin |
| Security access | `research/carplay/type111-security-access-matrix.md`, `research/carplay/type111-proxy-feasibility.md` | Honda Type 110 session/KDF state is jmcs-owned; no existing supported transfer to an independent proxy was found; Type111 fields remain unknown/MHI2 hypothesis |
| Rendering | `research/display/type111-render-path-options.md`, `research/display/companion-rendering-path.md` | ExternalDisplay owns the View host, but no supported companion frame/Surface handoff was found; Xposed path is prior art only |
| Twin boundaries | `research/simulator/digital-twin-architecture.md` | Synthetic tests validate model invariants only, not Honda/iPhone compatibility or runtime/deployment behavior |
| Decision and next task | `step-reports/42b-type111-architecture-decision.md`, `NEXT_ACTION.md` | jmcs entry, Honda Type111 schema/security/correlation, and renderer handoff block live work; LD_PRELOAD remains parked |

## Step 42A — Type111 correlation and companion handoff audit (2026-09-30)

| Area | Primary evidence | Finding |
|---|---|---|
| `/info` display shape | `step-reports/32-airplay-info-phone-path.md`; `research/carplay/honda-copy-displays-info.md` | Phone-facing `displays` CFArray is confirmed by static dataflow. The stock builder calls `ScreenCopyMain()` once and adds one descriptor. Field names are recovered; numeric `uuid` insertion is confirmed, but value semantics are unknown. |
| Type 110 Setup | `research/carplay/honda-stream-entry-schema.md`, `honda-screen-crypto.md`, `honda-mixed-stream-setup.md` | Request `type=110` and nonzero uint64 `streamConnectionID` feed per-screen crypto; response is `{type:110,dataPort}` from ephemeral listener. No UUID/ID binding found. |
| Type 111 stock behavior | `step-reports/38-type111-setup-security-contract.md`, `research/carplay/honda-mixed-stream-setup.md` | Unsupported type-111 entry is logged/skipped and adds no response; transaction can still succeed if common PlatformControl and supported entries succeed. Honda Type111 schema/security is absent. |
| ExternalDisplay host/API | `research/resources/ExternalDisplayOutService/AndroidManifest.xml`, `research/decompiled/ExternalDisplayOutService/.../ExternalDisplayOutService.java`, `InterfaceWindow.java`, `research/decompiled/ExternalDisplayLib/.../IExternalDisplayApService.java` | ExternalDisplayOutService owns Android View roots but `onBind` returns null; static `addView` is in-process. AP Binder controls LVDS/meter state and exposes no arbitrary frames/Surface/H.264 method. |
| CarPlay AP Binder | `research/resources/CarPlayService/AndroidManifest.xml`, `research/decompiled/CarPlayApServiceApiLib/.../ICarPlayApService.java`, `CarPlayService/.../DispControl.java` | Exported control API exists; `setVideoPath` toggles AV path 11, not a frame sink. No Type111 session/Surface/frame handoff found. |
| HondaHack output | `research/hondahack/hondahack-display-path.md`, `CLARITYLINK_OUTPUT_INTERFACE.md` | View insertion into ExternalDisplayOutService is demonstrated through Xposed; this is not a supported external service contract. |
| Model/readiness | `research/carplay/type111-display-stream-correlation.md`, `research/carplay/type111-security-fields.md`, `research/display/companion-rendering-path.md` | Existing response profile remains MHI2-derived and synthetic. No source-backed Honda model change; supported non-jmcs Type111/render handoff not found; live gates remain NOT READY. |

## Step 41G runtime probe and offline Type111 model validation (2026-09-30)

| Area | Evidence | Finding |
|---|---|---|
| Synthetic probe source/build | `src/claritylink-probes/preload/`, `tests/preload-probe/`, `research/deployment/runtime-preload-probe.md` | API 17 ARMv7 executable + preload source built with local NDK r23c; three artifact checks pass. Binaries were temporary and removed. No ARM runtime execution, device staging, or jmcs load occurred. |
| Runtime behavior | `step-reports/41g-runtime-preload-probe.md` | No qemu-user/ARM guest; absolute path, constructor execution, separator parsing, and missing preload behavior remain UNKNOWN. Future standalone parked probe plan does not clear jmcs-specific gates. |
| Existing Type111 models | `research/carplay/type111-offline-pipeline-status.md` | Negotiation 18, transport/parser/crypto 29, display/session 12, renderer 8, plus one host-only integration smoke passed. These are synthetic host models, not Honda wire acceptance. |
| Remaining protocol evidence | Same status note | Type111 response fields, display-stream correlation, KDF/key reuse, and physical ExternalDisplay receiver handoff are not established. Continue with source/capture evidence; no guessed fields. |
| Readiness | `NEXT_ACTION.md`, `PROJECT_STATE.md` | jmcs no-op load NOT READY; Type111 live NOT READY; offline evidence audit and companion API inventory are next. |

## Step 41D — SELinux and preload-path evidence audit (2026-09-30)

| Area | Primary evidence | Finding |
|---|---|---|
| Policy/context archive search | `research/carplay/step41d-selinux-load-environment.md` | No policy/context artifacts in enumerated tar archives or boot/recovery ramdisks; raw MMC image remains undecoded for policy |
| Init SELinux fingerprint | `root-startup.tar:init` strings; same research note | `selinux.`, `seclabel`, `setcon` strings confirm code-path fingerprints only; do not prove enforcing state or jmcs context |
| Runtime enforcement probe | `research/captures/jmcs-runtime-diff/20260929T160905Z/disconnected/selinux-enforcing.txt` and `.stderr` | `getenforce` unavailable; enforcement state UNKNOWN |
| AT_SECURE and candidate path | Same audit; Step 41C service report | `AT_SECURE` unknown; `/data/local/tmp` 0771 shell:shell is only a candidate, SELinux executable-map permission unproven |
| Decision | `step-reports/41d-selinux-load-environment.md` | All nine ext4 partitions inspected; no named policy/context files found; SELinux/AT_SECURE/path access unknown; Step 42 not ready |

## Step 41D2/41D3 — raw ext4 read-only inspection (2026-09-30)

| Area | Primary evidence | Finding |
|---|---|---|
| GPT/partition geometry | `research/carplay/step41d-selinux-load-environment.md` | Nine named ext4 partitions, exact starts/ends/offsets/sizes/UUIDs recorded; filesystem roles not inferred |
| Journal safety | Same note; raw superblock feature flags | Seven filesystems set `EXT4_FEATURE_INCOMPAT_RECOVER`; no mounting/replay attempted |
| Reader/method | Same report | e2fsprogs `debugfs` 1.47.4 run without `-w` against temporary partition copies; no mounts or journal replay |
| Policy/context search | Same report and research note | No named policy/context files in recursive walks of all nine ext4 filesystems |
| Binary/path evidence | Same report | APP `/bin/jmcs` hash matches known image; UDA `/local/tmp` is 0771 shell:shell with no xattr |
| Decision | Same report | Filesystem inspection complete; SELinux mode/domain, AT_SECURE, and mapping permission remain unknown; live load not ready |

## Step 40E4 — zero-write privilege path audit (2026-09-29)

| Area | Primary evidence | Finding |
|---|---|---|
| SuperSU client/daemon | `research/runtime/supersu-execution-path.md`, `supersu-write-side-effects.md` | SuperSU 2.77-family; partial static path trace; no exact upstream binary match; `su -c` zero-persistent-write NOT PROVEN because stripped control flow/open flags and daemon/policy/log paths remain unresolved |
| ADBD | `research/runtime/adbd-privilege-model.md` | Archived defaults `ro.secure=1`, `ro.debuggable=0`, user/release-keys; prior shell UID 2000; root adbd without `su` NO on archived configured evidence |
| Alternative privileged paths | `research/runtime/alternative-root-paths.md` | No approved narrow root read proxy or useful SUID/SGID candidate found; `bugreport`/`dumpstate` is broad and may signal/write, not run or approved |
| 40F-Lite / required datum | `research/runtime/collector-privilege-matrix.md`, `step40f-lite.md` | Existing Step 40E capture already provides meaningful ordinary-shell evidence; fresh maps/smaps/fd remain denied and are not recoverable from older process epochs |
| Threat model / review packet | `research/runtime/privilege-threat-model.md`, `step40e4-review-packet.md` | Zero-write definition distinguishes application writes, transient IPC/RAM/kernel state, tmpfs, and atime; independent review NOT PERFORMED |
| Decision | `step-reports/40E4-zero-write-privilege-path.md` | No justifiable privileged path; Step 40F/41 NOT READY; Type111 disabled |

## Step 40E3 — SuperSU provenance and side-effect review (2026-09-29)

| Area | Primary evidence | Finding |
|---|---|---|
| Binary identity | `research/platform/honda-root-path.md`, `step-reports/40e3-supersu-provenance-static-review.md` | `/system/xbin/su` is a 75,348-byte Chainfire SuperSU-family `2.77:SUPERSU`; SHA-256 `d95fdbb551aca66d8a81471ea7683f58dba75a09d5cdc4712209b955574eab26` |
| Acquisition provenance | September 18 backup `system-vendor.tar`; September 25 forensic `filesystems/system.tar`; `research/inventory/backup-checksums.json`; forensic `SHA256SUMS` | Three full-system copies agree on binary bytes and owner/mode `0:0 / 06777`; these are captures of the modified unit, not a factory-ROM baseline |
| Mode attribution | `research/platform/honda-root-path.md` | Mode is uniquely permissive compared with other special-bit binaries; no inspected HondaHack code sets `su` to `06777`; exact actor/date UNKNOWN |
| HondaHack privilege path | Local ignored `research/hondahack/artifacts/hondahack-installed.apk`, statically inspected DEX/resources | APK 7.7.7 uses embedded libsuperuser with `su`, prepends SuperSU log deletion, and contains persistent root changes; APK binary not executed |
| Root startup modification | APK resource `install_recovery2_mitsubishi.sh`; system archive `system/etc/install-recovery2.sh`; `root-startup.tar:init.rc` | Payload hashes match; init launches a USB-polled script that executes a supplied `recovery.sh` as root; hazardous unrelated path, excluded from collector |
| Zero-write invocation | Binary imports/strings plus [official Chainfire How-To](https://su.chainfire.eu/) | Direct `su -c` side effects remain unknown; zero-write guarantee absent; Step 40F NOT READY |
| Review | Step 40E3 report | ECC security-review workflow used; independent reviewer unavailable; no independent approval claimed |

## Step 40E2 — offline bundle exhaustion and privileged-read preparation (2026-09-29)

| Area | Primary evidence | Finding |
|---|---|---|
| Bundle inventory | `tools/honda-readonly-preflight/bundle_inventory.py`, `step-reports/40e2-privileged-read-preparation.md` | 1,944 artifact/manifest entries represented; all 1,944 capture hashes matched; inventory and detailed TID/network derivatives live beside raw evidence outside Git |
| Proc permission | `research/platform/honda-proc-access.md` | UID 2000 denied maps/smaps/fd; ptrace credential gate is high-confidence based on related Tegra source, not exact Honda confirmation; page size UNKNOWN |
| Existing root facility | `research/platform/honda-root-path.md` | `/system/xbin/su` ARM SuperSU-family binary and `su -c` use proven in earlier read-only sessions; preserved archive mode 06777 is unsafe; live mode/hash and persistence effects UNKNOWN |
| Prepared collector | `tools/honda-readonly-preflight/privileged.py`, `privileged_session.py`, `session.py` | Fixed enum allowlist, exact UID and process checks, root binary fingerprint/mode gate, host-only raw outputs, three-phase prompts, car-off success/abort messages |
| Decision | Step 40E2 report | Full session simulator passes, but the mode gate rejects the preserved `su`; vehicle session NOT READY; Step 40F/41 NO; Type111 disabled |
| Review | Step 40E2 report | ECC security-review and terminal-ops used; independent ECC reviewer unavailable; no independent approval claimed |

## Step 40E — parked read-only Honda runtime preflight (2026-09-29)

| Area | Primary evidence | Finding |
|---|---|---|
| Read-only collector | `tools/honda-readonly-preflight/collector.py`, `README.md` | Fixed read-only operations, explicit parked/disconnected gates, one-device selection and kernel/Android-property fingerprint gates, no arbitrary command/upload/write path, per-command timeout/output cap, host-only raw storage |
| Host parsers/analyzer | `tools/honda-readonly-preflight/parsers.py`, `analyze.py`, `tests/honda/test_readonly_preflight.py` | Synthetic maps/smaps/status/signal/task/network/load-bias/gap/privacy tests; no ADB dependency |
| Live attempt | `research/platform/honda-live-runtime.md`, `step-reports/40e-readonly-runtime-preflight.md` | Three phases completed through legacy `adb shell`; target fingerprint matched; same `jmcs` PID/start time persisted; maps/smaps denied; thread snapshots partial while connected; raw bundle and analysis remain host-only |
| Hook/runtime gates | `research/carplay/honda-runtime-addressing.md`, `honda-veneer-allocation.md`, `honda-thread-rendezvous.md`, `honda-runtime-patch-lifecycle.md`, `honda-hook-safety.md` | Maps/smaps denied; no live addresses/gaps; process signals and thread snapshots captured with connected-phase partiality; Step 40F and Step 41 remain NO |
| Verification/review | Step 40E report | preflight 35; Honda 90/1 skipped, interposer 14, transport+negotiation 47 + 31 subtests, renderer 8; ECC guidance used; independent reviewer unavailable |

## Step 40D — kernel provenance and API-17 ARM runtime (2026-09-29)

| Area | Primary evidence | Finding |
|---|---|---|
| Official source | `research/platform/honda-ada01-source.md` | Honda/Panasonic ADA01 archive SHA-256 recorded; safe inventory/extraction; Linux 3.4.108 generic Tegra, no VCM30T30; related source only |
| Target kernel | `research/platform/honda-kernel-provenance.md`, `honda-kernel-config.md` | Forensic copy hash recorded; exact target 3.1.10+; modules corroborate SMP/preempt/ARMv7; config and VM page size unknown |
| API 17 ARM image | `research/platform/api17-arm-runtime.md` | Official image hash verified; Google emulator rejects ARM in both engines; generic QEMU lacks Goldfish; no guest tests |
| Runtime gate | `research/carplay/honda-executable-memory.md`, `honda-icache.md`, `honda-thread-rendezvous.md`, `honda-runtime-patch-lifecycle.md` | No RX/RW/cache/Thumb/veneer/signal/futex/rendezvous runtime proof; Step 41 NO; Step 40E read-only capture complete with maps/smaps permission limits |
| Verification | `step-reports/40d-honda-kernel-and-api17-runtime.md` | Honda 55 passed/1 skipped, interposer 14, transport+negotiation 47 + 31 subtests, renderer 8; host tests only |
| Review | Step 40D report | ECC skill guidance applied; independent reviewer endpoint unavailable; self-review remains open, not external ECC approval |

## Step 40B — reversible Thumb-2 call-site model (2026-09-29)

| Area | Primary evidence | Finding |
|---|---|---|
| Exact call sites | `research/carplay/honda-thumb-hook.md`, exact local `jmcs` ELF and objdump | `0x28a158` bytes `f8 f7 bc fd` → `0x282cd4`; `0x28af72` bytes `fa f7 b5 fa` → `0x2854e0`; both direct 32-bit Thumb `BL` |
| Encoding / veneer | `src/claritylink-honda/thumb_call.py`, `tests/honda/test_thumb_call.py` | Host-confirmed BL decoder/encoder, branch-range boundaries, explicit Thumb-pointer bit; 12-byte literal veneer uses r12, preserves args/LR/SP |
| Synthetic execution | `tests/honda/test_thumb_call.py`, Unicorn 2.1.4 isolated under `/tmp` | Transaction-patched callsite executes caller → veneer → representative shim → stand-in callee → caller continuation; verifies registers/SP, restores exact original call bytes. This is not Honda runtime evidence |
| Patch / restoration | `src/claritylink-honda/mock_hooks.py`, `research/carplay/honda-hook-restoration.md` | Host bytearray transaction preflights group, verifies exact restore, fails closed on unknown bytes and stale process epoch; no process writer |
| Semantics | `src/claritylink-honda/modes.py`, Honda hook tests | NOOP/OBSERVE INFO and Setup preserve exact stock result; observations are count/class only and bounded |
| Executable memory gate | `research/carplay/honda-executable-memory.md`, `honda-hook-safety.md` | Offline synthetic harness READY; target veneer allocation, W^X/page permissions, cache sync, thread coordination, and runtime restore remain UNKNOWN/NOT READY; Step 41 and Type111 live test stay disabled |
| Review / verification | `step-reports/40b-thumb2-reversible-hook.md` | ECC skills/checklist applied with diff review; no dedicated ECC reviewer endpoint in this environment; focused and affected-suite results recorded in report |

## Step 40 — Honda hook boundary (2026-09-29)

| Area | Primary evidence | Finding |
|---|---|---|
| Exact build | src/claritylink-honda/elf_identity.py, targets.py, research/carplay/honda-hook-fingerprints.md | Whole ELF and .text hashes, size, ELF32/little/ARM/ET_DYN verified against local ignored jmcs; no GNU build-id |
| Setup ABI | research/carplay/honda-hook-abi.md, honda-hook-points.md | Setup r0=session, r1=request, r2=responseOut; caller at 0x28af72 checks status and passes response to synchronous serializer |
| Candidate hook set | research/carplay/honda-hook-points.md, honda-hook-fingerprints.md | Narrow call-site candidates 0x28a158 (/info builder) and 0x28af72 (Setup); session start/teardown coordination needed before persistent mode |
| Addressing | src/claritylink-honda/addressing.py, research/carplay/honda-runtime-addressing.md | Synthetic PT_LOAD/maps load-bias and Thumb-bit resolver; no live /proc read |
| Mock hook lifecycle | src/claritylink-honda/mock_hooks.py, hook_gate.py, tests/honda/ | Exact gates, all-or-none mock activation, original-byte restore and retry; not a live writer |
| Modes/readiness | src/claritylink-honda/modes.py, research/carplay/honda-hook-safety.md | OFF/NOOP/OBSERVE host semantics work; AUGMENT requires extra gates; trampoline/veneer and live rollback not ready |
| Verification | step-reports/40-honda-hook-harness.md | 104 maintained tests pass (31 subtests); no live hook or Type111 test |

## Step 39 — Host-only Display-B interposer (2026-09-29)

| Area | Primary evidence | Finding |
|---|---|---|
| `/info` augmentation | `src/claritylink-interposer/server_info.py`, `research/carplay/display-b-interposer.md` | Copy-on-write additive display model; unknown fields preserved; no session resource created by advertisement |
| Stock-first Setup | `src/claritylink-interposer/setup_interposer.py`, `research/carplay/type111-response-model.md` | Exact original request object delegated; stock response copied and appended only after project setup; minimal and prior-art clone profiles are configurable |
| Ownership/rollback | `src/claritylink-interposer/transaction.py`, `listener.py`, `research/carplay/type111-rollback.md` | Fake port-0 listener, ordered idempotent cleanup, serializer failure rollback; no OS listener |
| Lifecycle/security | `src/claritylink-interposer/lifecycle_coord.py`, `models.py`, `research/carplay/type111-lifecycle.md`, `type111-security-contract.md` | ACTIVE only after modeled stock SessionStart; redacted/wiped secret buffers; Type111 KDF remains unverified |
| Hook safety | `research/carplay/honda-hook-abi.md`, `hook-safety-contract.md` | Data-only binary/prologue exact-match gate; no verified prologue contract or hook harness |
| Verification | `tests/interposer/`, `tests/integration/test_display_b_flow.py`, `step-reports/39-host-interposer.md` | 83 maintained tests pass across `tests/` and renderer tests (31 subtests); focused set 62 pass; no live compatibility claim |

## Step 38 — Honda Type111 Setup and security contract (2026-09-29)

| Area | Primary evidence | Finding |
|---|---|---|
| Mixed SETUP | research/carplay/honda-mixed-stream-setup.md, honda-type111-rejection.md | Unsupported 111 logs and continues without error/status/response mutation. Overall Setup succeeds conditionally on all supported handlers and final PlatformControl; valid stock response entries survive; no 111 rollback |
| Delegation | research/carplay/honda-type111-intercept.md, type111-transport-model.md | Original-request stock delegation is supported by Honda CFG; append only after stock success |
| Type111 descriptor/response | research/carplay/type111-request-model.md, type111-response-model.md | Honda proves only generic type and Type110 fields. Pinned MHI2 source reads streamConnectionID, clones the full descriptor and sets dataPort/streamID=111; Honda Type111 schema remains unknown |
| KDF | research/carplay/type111-security-contract.md, screen-crypto.md, stream-connection-id.md | Honda Type110 KDF uses unsigned decimal ID text in separate AirPlayStreamKey/IV salts, SHA512(salt || 16-byte master), first 16 digest bytes |
| Response ownership/lifecycle | research/carplay/honda-setup-response.md, type111-lifecycle.md, type111-rollback.md | Mutable response streams array permits structural append. Project Type111 teardown must be independently owned; Honda only handles stock 100/101/110 |
| Offline model/tests | src/claritylink-negotiation/, tests/negotiation/test_setup_contract.py, step-reports/38-type111-setup-security-contract.md | Stock-first transaction, synthetic KDF and lifecycle models; 29 transport + 18 negotiation tests pass; no live listener/hook or real key |
| Readiness | step-reports/38-type111-setup-security-contract.md | Offline model ready; Honda Type111 response acceptance, phone trigger and Type111 KDF compatibility remain unknown; live TCP test not ready |

## Step 37 — Honda VideoConfig to media buffer (2026-09-29)

| Area | Primary evidence | Finding |
|---|---|---|
| Config-to-parser link | `research/carplay/honda-video-config.md`, `honda-h264-format.md` | Type-1 property callback parses an avcC-like SPS/PPS record, derives NAL length width from config byte 4, and stores it in the context consumed by Type-0 media processing |
| Parameter sets | `research/carplay/honda-video-config.md`, `mc-screenstream-input.md` | Honda emits four-byte start-code-prefixed SPS/PPS and prepends stored config once to the next normal converted media buffer |
| Video records | `research/carplay/honda-h264-format.md`, `mc-screenstream-input.md` | Normal converter supports 1/2/4-byte length records and pushes one output buffer per screen message; width 3, zero-run normalization details, and exact AU semantics remain unresolved |
| Direct mode | `research/carplay/honda-h264-format.md`, `mc-screenstream-input.md` | Callback context `+0x11` selects whole-body copy, bypassing record conversion and config prepend; active Type-110 value is unknown |
| Crypto/timestamp/sink | `research/carplay/honda-screen-crypto.md`, `honda-screen-timestamp.md`, `mc-screenstream-input.md` | Body CTR state advances before opcode dispatch; timestamp converter/timebase and concrete active media sink remain unknown |
| Type 111 | `research/carplay/type111-transport-model.md`, `type111-step38-contract.md` | Honda logs unsupported type 111 and continues the SETUP array loop; mixed-entry rollback and request/security contract remain open |
| Implementation/readiness | `src/claritylink-transport/`, `tests/transport/test_media_pipeline.py`, `step-reports/37-video-config-media-pipeline.md` | Synthetic offline config/framing/record receiver model added; 29 tests pass; executable Type111 and live test are not ready |

## Step 34 — AltScreen transport/presentation split (2026-09-29)

| Area | Primary evidence | Finding |
|---|---|---|
| Honda screen crypto | `research/carplay/screen-crypto.md`, `stream-connection-id.md` | Type-110 derivation inputs are session master material (16 bytes) plus `streamConnectionID` (`uint64`); type is dispatch-only, not a derivation input; no UUID input observed |
| Socket/framing | `research/carplay/honda-screen-framing.md`, `accepted-fd-dataflow.md`, `screen-tcp-framing.md` | Accepted fd is owned by per-thread `NetSocket`; dedicated listener binds the transport endpoint, but persistent object offsets and Honda TCP grammar remain partial/unknown |
| MHI2 Type 111 | `research/carplay/prior-art-altscreen.md`, `type111-request-model.md`, `type111-response-model.md` | Pinned current source `c2f811f...` clones descriptors, preserves unknown fields, derives per-screen crypto from stock session material + ID, and separates Type-111 transport from UI control; target-specific evidence only |
| Control plane | `research/carplay/honda-platform-control.md`, `transport-vs-presentation.md` | Honda control symbols and mode/UI helpers exist; exact suggest/show/stop/ViewArea semantics remain unknown; matching strings absent |
| Display correlation | `research/carplay/display-stream-correlation.md`, `claritylink-display-b-architecture.md` | UUID reclassified presentation/capability identity; no Honda UUID-to-stream-ID or crypto link demonstrated |
| Delegation | `research/carplay/honda-type111-intercept.md` | Step 34 strategy was tentative; Step 38 proves Honda non-fatal skip and recommends passing original request, then appending after stock success |
| Feature tokens | `research/carplay/prior-art-altscreen.md` | Modern token requirement is version-dependent; whether Type 111 predates tokens remains unknown |
| Decision | `step-reports/34-transport-presentation-split.md` | Offline executable transport implementation NO; live transport test NO; biggest blocker is Honda Type-111 contract plus safe mixed-stream delegation |

## Step 33 — display ↔ stream connection binding (2026-09-29)

| Area | Primary evidence | Finding |
|---|---|---|
| Stream identifier | `research/carplay/stream-connection-id.md`, `honda-screen-session-binding.md` | Type-110 reads `streamConnectionID` as uint64 and passes it to screen AES key/IV derivation; persistence/accepted-socket mapping remain partial |
| Display identity | `research/carplay/honda-display-uuid-flow.md` | Phone-facing numeric `uuid` property from `ScreenCopyMain`; no use found in analyzed SETUP path |
| Correlation | `research/carplay/display-stream-correlation.md` | No UUID ↔ connection-ID structure found; display-to-stream binding UNKNOWN |
| Type 111 models | `research/carplay/type111-request-model.md`, `type111-response-model.md`, `honda-type111-intercept.md` | Honda rejects 111; request, response, crypto, and partial delegation remain unproven |
| Architecture | `research/carplay/claritylink-display-b-architecture.md` | Offline server-info boundary model ready; complete Type-111 model/live connection test not ready |

Step report: `step-reports/33-stream-connection-binding.md`.

## Step 30 — AltScreen negotiation loop (2026-09-29)

| Area | Primary evidence | Finding |
|---|---|---|
| Server-info builder | research/carplay/honda-server-info.md | DWARF signature recovered; requests displays and inserts it in mutable result dictionary |
| Capability send path | research/carplay/honda-display-capability-send-path.md | Local insertion confirmed; serializer/network send and phone-facing status UNKNOWN |
| Display data | research/carplay/honda-display-capabilities.md, honda-display-uuid-flow.md | One main-display array entry; mutable container; descriptor wire semantics and UUID correlation unresolved |
| Type 111 | research/carplay/honda-type111-rejection.md, honda-stream-type-parser.md | 100/101/110 stock dispatch, 111 invalid path at 0x2861f6; exact external status unresolved |
| Offline models | research/carplay/type111-response-model.md, display-stream-correlation.md | Type-111 response only sketched from prior art; binding UNKNOWN |
| Decision | research/carplay/claritylink-display-b-architecture.md, display-b-interposer.md | Two-hook sufficiency UNKNOWN; implementation/test readiness NO |

Step report: step-reports/30-close-altscreen-negotiation-loop.md.

## Step 29 — display property caller, SETUP parser, and binary identity

| Area | Primary evidence | Finding |
|---|---|---|
| Acquisition identity | `research/carplay/jmcs-acquisition-identity.md`, `research/carplay/jmcs-address-map.md` | Exact `system/bin/jmcs` member extracted from immutable acquisition; SHA/ELF/symbol/address evidence matches analyzed image |
| Display property | `research/carplay/copy-displays-indirect-calls.md`, `honda-display-capabilities.md` | Direct caller builds a one-element `displays` property array; wire serializer/send edge remains unknown |
| Setup request | `research/carplay/honda-setup-request.md`, `honda-stream-type-parser.md` | Body parsed as plist; `streams[]` entry integer `type`; 100/101 audio, 110 screen, 111 invalid-type path |
| Correlation/gating | `research/carplay/display-stream-correlation.md`, `honda-alt-screen-gating.md` | No UUID/ID correlation; whether phone requires second descriptor remains unknown |

## Step 29 — caller/parser recovery boundary (2026-09-29)

Step 29 was offline-only. Available tracked artifacts do not include the matching `jmcs` ELF/relocations/data/DWARF needed to recover indirect `CopyDisplaysInfo` function-pointer storage, nor the `_connectionHandleMessage`/Setup request-read disassembly needed to identify an incoming stream-type key or Type-111 branch. The Step 28 dictionary remains local-only; the Step 27 response send path remains confirmed. Type-111 behavior, multiplicity, UUID correlation, and second-display advertisement requirement are UNKNOWN. No implementation or live work. See `step-reports/29-display-caller-and-stream-parser.md` and the eight linked research notes.

## Step 28 — Honda display capability gating (2026-09-29)

`AirPlayReceiverSessionScreen_CopyDisplaysInfo` returns one mutable dictionary from one `ScreenCopyMain()` object. Recovered keys: `edid`, `features`, `maxFPS`, `widthPhysical`, `heightPhysical`, `widthPixels`, `heightPixels`, `uuid`; numeric `uuid` setter path and masked `features` semantics need clarification. No display array/loop exists in this function. Generated disassembly contains no direct call to it; indirect caller remains possible. No parent message, serializer, protocol phase, or phone-facing edge is established. Request-side type parsing, Type-111 acceptance, and display/stream correlation remain unknown. No live work or code was performed. See `step-reports/28-honda-display-capability-gating.md`, `research/carplay/honda-display-capabilities.md`, `honda-copy-displays-info.md`, `honda-identification-receiver-info.md`, `honda-alt-screen-gating.md`, `honda-stream-type-dispatch.md`, `display-stream-correlation.md`, and `altscreen-control-plane.md`.

# ClarityLink evidence index — 2026-09-29

## Step 27 — Honda SETUP response send path (2026-09-29)

`_connectionHandleMessage` (`0x28a30c`, `AirTunesServer.c`) directly calls `AirPlayReceiverSessionSetup` at `0x28af72` with session/request/output in `r0/r1/r2`; the response output slot is passed unchanged to `_requestSendPlistResponse` at `0x28afba`. The helper serializes it with `CFPropertyListCreateData(format=0xc8)`, installs binary plist CFData bytes/length as an HTTP body, and the caller releases the object after conversion. `_connectionHandleMessage` sends via `HTTPConnectionSendResponse` (`0x29dbe4`). This confirms the same `streams` array containing stock `type=110` and `dataPort` reaches the phone-facing response path. The static TCP write path is `_HTTPConnectionRunStateMachine` -> `SocketWriteData` -> `writev@plt`; runtime packet segmentation, server callback registration, and request route token remain unknown. Immediate post-Setup/pre-serializer is a structural candidate, not live-hook approval. Display capability signaling and Type-111 correctness remain unknown. See `step-reports/27-honda-setup-send-path.md`, `research/carplay/honda-setup-response.md`, `honda-response-caller.md`, `honda-response-ownership.md`, `honda-response-serializer.md`, `honda-phone-send-path.md`, `honda-stream-entry-schema.md`, `honda-hook-abi.md`, and `display-b-fixture.md`.

## Step 26 — Honda Setup response ABI (2026-09-29)

Local ignored `jmcs` disassembly proves the Setup response accumulator is a mutable CF-style dictionary; stock stream response is represented by a `streams` CFArray whose entry has Honda-inserted `type=110` and dynamic `dataPort`. `_AddResponseStream` is at `0x284db8`; Setup is at `0x2854e0`; dataPort insertion is at `0x286160`. `CopyDisplaysInfo` (`0x287ae0`) separately returns one main-screen dictionary from `ScreenCopyMain` and does not loop. Setup publishes its response through an output pointer; its separate completion callback receives status/context, not the response. The output-pointer caller, serializer/network write, full formal ABI, and ownership remain unknown. Generic HTTP plist serializer `0x289f60` has no proven Setup call edge. Local geometry is not established as wire descriptor content. Type 111 and `altScreen` remain prior-art/unknown for Honda. Fixture uses explicitly synthetic UUID/port labels and preservation tests. Details: `research/carplay/honda-setup-response.md`, `honda-display-descriptor.md`, `honda-dataport-field.md`, `honda-response-serializer.md`, `honda-hook-abi.md`, `display-b-fixture.md`, and `step-reports/26-honda-setup-response-abi.md`.

## Step 25 — AltScreen prior art pivot (2026-09-29)

Apple WWDC19 officially documents multiple simultaneous H.264 cluster streams and vehicle-selected instrument-cluster content, with R15 required for the described new feature set. Pinned xcertplay source (`3753867f0dd0e5c03490b987fb9df49b8ac96472`) defines main type 110 and alternate type 111, distinct display UUIDs, a display list, `altScreen`, and per-stream `dataPort` setup responses. Pinned Harman source (`c2f811f1a5c84dae3a62f4cf9b4a9e65fc3f7b3c`) implements a Type-111 receiver/interposer on MHI2. Honda still shows one `gMainScreen`, `ScreenCopyMain`, and singleton proxy registration; no compatible descriptor/SETUP extension is proven. `mc_dev_attach` is fallback-only in the strategy, not yet bypassed on Honda. No ptrace, vehicle, or code implementation occurred. Details: `research/carplay/prior-art-altscreen.md`, `stream-type-111.md`, `altscreen-capabilities.md`, `altscreen-control-plane.md`, `altscreen-data-port.md`, `honda-altscreen-gap-analysis.md`, `claritylink-display-b-architecture.md`, and `step-reports/25-altscreen-prior-art-pivot.md`.

## Step 24 — single live registry-reader attempt (2026-09-29)

Using the reviewed ARMv7/API17 binary with iPhone disconnected, fresh `/system/bin/jmcs` PID 19905 and maps were verified. Current load bias `0x40001000`; static VA `0x35acbc` derived cell `0x4035bcbc` in readable `rw-p` memory. The single 4-byte `process_vm_readv` call returned `READ_STATUS=UNSUPPORTED` (`ENOSYS`); no target bytes were read and no registry JSON exists. PID 19905 remained `/system/bin/jmcs`, temporary reader removed, ADB disconnected. No retry or fallback. Raw cmdline/maps and reader output are local/ignored in `research/captures/registry-reader-live-20260929/`. See `step-reports/24-registry-reader-live-unsupported.md`.

## Step 23 — ARMv7/API 17 reader build and offline audit (2026-09-29)

Official Android NDK r23c DMG SHA-1 verified; C reader builds as ARM EABI5 PIE for `armeabi-v7a`, API 17. Exact ARM EABI header gives `process_vm_readv` syscall 376 and source asserts it. ELF/ISA, imports against saved Honda firmware, minimal dependencies, 10,272-byte bound, and safety audit pass; synthetic tests pass. Kernel support is UNKNOWN (likely Linux 3.1.10); `ENOSYS` cleanly stops. No emulator or vehicle execution occurred. Binary SHA-256 and reproducible command: `research/carplay/registry-reader-armv7-build.md`; session procedure: `research/carplay/runtime-registry-reader.md`; step report: `step-reports/23-registry-reader-armv7-build.md`.

## Step 21 — minimum `mc_devs` observation design (2026-09-29)

Registry-only first observation is designed; no live score capture initially. Known chain: `mc_devs` cell -> manager -> manager `+0x08` list head -> node (`+0` next, `+4` list bookkeeping, `+8` interface) -> interface `+0/+4` callbacks. Static disassembly confirms context aliases the interface pointer and tail append makes traversal order insertion order. Node allocation is `0x0c`; estimated maximum target memory is `8 + 20N` bytes (2,568 at a 128-node cap). `process_vm_readv` preferred if supported/permitted; target support unknown. Initial iPhone state disconnected. Not ready for execution until reader review. See `step-reports/21-runtime-read-design.md`, `research/carplay/runtime-registry-read-plan.md`, `research/carplay/runtime-registry-layout.md`, and `research/carplay/runtime-device-registry.md`.

## Step 22 — reader implementation/offline review (2026-09-29)

Purpose-built reader and resolver implemented. Synthetic tests and forbidden-import review pass. Two-pass consistency and one additional bounded attempt give a total maximum of 10,272 requested/read bytes; no process suspension or write path. At Step 22 the ARMv7 build was unverified; Step 23 supersedes that status with a checksum-verified r23c/API17 build and full offline audit. Kernel support remains unknown. See `step-reports/22-registry-reader-implementation.md`, `step-reports/23-registry-reader-armv7-build.md`, and `research/carplay/runtime-registry-reader.md`.

Step 20: static symbol/DWARF and call-path audit found no safe pre-existing devmgr dump/list or candidate match trace. The manager loop does not log score/interface/winner; raising log level cannot expose missing callsites. No CLI diagnostics or devmgr Binder/IPC dump identified. `jmcs`-owned TCP port-5000 runtime listeners remain statically unattributed; ScreenSession's traced listener asks for port 0. See `step-reports/20-jmcs-diagnostic-discovery.md`, `research/carplay/jmcs-diagnostics.md`, and `research/carplay/port-5000.md`.

Step 11 update: see `step-reports/11-primary-screen-completion.md`. The local tracked corpus does not include the detailed listener/parser disassembly slice needed for port, first read, or TCP framing. No H.264/decoder/Surface edge has been proven from the callback path.

Step 14: `mc_stream_link` and all direct callers were traced. Calls are in generic PBS pipeline construction; the active CarPlay sink still is not identified because the CarPlay screen path reaches device attachment through indirect device/factory dispatch. See `step-reports/14-active-media-sink.md`, `research/carplay/mc-stream-link.md`, and `active-carplay-sink.md`.

Step 16: generic manager dispatch is decoded: registry entries are ranked by interface slot +0 and selected attach dispatch uses slot +4; `devmgr_app_register` is the registration API. The winning entry and comparator for `"CarPlay Screen"` remain unknown, as do its concrete attach callback and downstream sink/decoder/Surface ownership. See `step-reports/16-carplay-registration-match.md` and `research/carplay/device-registration.md`.

Step 13: DWARF resolves the media vtable role as `mc_stream_sink_ifc.process_data` (+0x14) and documents the MediaCodec backend context plus Surface setter/configuration API. The concrete CarPlay sink implementation is not tied to the backend. See `step-reports/13-media-vtable-decoder.md` and `research/carplay/media-vtable.md`.

Step 12 supersedes the Step 11 listener/first-read limitation: exact local `jmcs` is present and its VA/file offset map is validated; see `research/carplay/jmcs-address-map.md` and `step-reports/12-jmcs-deep-slice.md`. Listener binds port 0, recovers the selected port with `getsockname`, writes it to `CFDictionarySetInt64`; accepted descriptor flows into `NetSocket_ReadInternal` -> `recv` (request 128 bytes). TCP grammar and media decoder linkage remain open.

| Question | Evidence | Verdict | Remaining proof |
|---|---|---|---|
| Android output target | Live display/sysfs/SF snapshots and screencap | Display 1 HDMI, 800×480, about 60 Hz, layer stack 1 | None for Android logical mode |
| HondaHack Screen Casting path | Targeted 7.7.7 APK decompilation plus Screen Casting snapshot | Display 0 captured at 400×240 ARGB_8888; Bitmap via shared MemoryFile/PFD; ImageView/View injected in Honda ExternalDisplay root; full-window Display 1 output | Supported ClarityLink host acquisition/lifecycle |
| Advanced Meter path | Same APK trace and state snapshots | Uses same Xposed-injected externaldisplay View host; content is meter/navigation widgets | Exact runtime child-view to layer mapping |
| Android Display 1 crop | Three SF state dumps | Full-frame 800×480 layers; no smaller Android crop observed | None for current evidence |
| Physical Navigation bounds | Paired Display 1 factory image and full-cluster photo | UNKNOWN. Photo/capture difference supports downstream composition but gives no calibrated rectangle; not currently a Step 2 blocker | Defer exact mapping unless renderer implementation requires it |
| Framebuffer format | sysfs reports bpp 0 and stride 3200 | UNKNOWN; no raw framebuffer access | Driver metadata only if a later need arises |
| ClarityLink renderer prototype | src/claritylink-renderer and host tests | Synthetic 800×480 RGBA source, explicit frame contract, mock attach/submit/clear/destroy, API 17 View backend skeleton | Step 3: executable offline output prototype; isolate privileged Honda root adapter; later one reversible parked-car proof |
| Primary CarPlay display/session | j_config.xml, focused jmcs disassembly, research/carplay/primary-display-session.md | One configured 800×480, max 30 FPS, hifi-touch main screen; actual UUID/wire fields unknown | Find serializer/setup boundary and actual session values |
| Runtime device registry | Steps 18, 19, 23, 24; `research/carplay/runtime-device-registry.md` | Prior `/proc/26577/mem` read denied. Step 24's one bounded read attempt on current PID 19905 returned `ENOSYS`; no memory bytes or JSON. The `mc_devs` head/winner remain unknown. | Offline design/review of a minimal read-only ptrace path; do not retry `process_vm_readv` or attach until stop/resume risks and recovery are separately reviewed |
| Device-manager registration winner | `step-reports/17-carplay-registration-winner.md`, `research/carplay/device-match-semantics.md`, local ignored `jmcs` ELF with symbols/DWARF | Generic max unsigned slot-0 result confirmed (strict >, initial 0); registration node interface at +8; direct media/I/O registration routes identified. Exact runtime candidate for `"CarPlay Screen"` unresolved | Capture registry node/interface/context/order at attach or identify exact runtime registration producer; do not infer attach/sink/decoder path |
| Screen transport / framing / H.264 | `step-reports/37-video-config-media-pipeline.md`; `research/carplay/honda-screen-header.md`, `honda-screen-read-loop.md`, `honda-screen-crypto.md`, `honda-screen-framing.md`, `honda-video-config.md`, `honda-h264-format.md`, `mc-screenstream-input.md` | Honda 128-byte plaintext header, LE32 body size, byte discriminator, and body-only continuous AES-CTR are recovered. Type-1 config is avcC-like; SPS/PPS become Annex-B prefixes and feed the next normal type-0 buffer. Normal type-0 conversion supports 1/2/4-byte records; direct-body mode, zero-run normalization, exact AU semantics, timestamp timebase, and active sink remain unresolved. Offline synthetic receiver model and 29 tests exist; no executable Type111 receiver/live test. | Resolve Type111 SETUP/security inputs plus mixed-entry failure/rollback semantics offline |
| Primary screen start/control path | exact `jmcs` ELF/hash, `jmcs-address-map.md`, `accepted-fd-dataflow.md` | IPv4 TCP listener binds port 0; `getsockname` port stored and passed to `CFDictionarySetInt64`; accepted fd wrapped and first `recv` requests 128 bytes | Resolve dictionary key/external advertisement semantics and TCP grammar; runtime endpoint varies |
| Video stream callback/output | `ScreenStreamProcessData`, `mc_ScreenStreamProcessData`, DWARF sink interface and backend layout; `research/carplay/video-callback-trace.md`, `carplay-decoder.md` | `mc_stream_push_data` dispatches through `mc_stream_sink_ifc.process_data` (+0x14); MediaCodec and surface APIs exist, but concrete CarPlay sink-to-decoder and Surface edges are unproven | Resolve callback/context xrefs to H.264 pipeline/MediaCodec configure and output target |
| Multi-display receiver support | research/native/receiver-multidisplay-audit.md | Partial generic array/stream lifecycle; Honda initialization selects one main screen and proxy callback is singleton | Establish if a compatible receiver extension can safely dispatch a second independent stream |
| Second CarPlay display/session | `research/carplay/second-display-session.md`, `research/carplay/primary-screen-end-to-end.md`, and `src/carplay-session-model/model.py` | Candidate Display B model only; UUID, role, accepted session, stream ID, application assignment, and wire schema unknown | Resolve missing setup transport/schema, wake producer, and decoder/output consumer; consider narrowly scoped passive evidence after endpoint identification |
| Identification serialization | research/iap2-identification.md and research/carplay/identification-schema.md | No packet bytes, IDs, order, byte order, framing, or checksums recovered; display-info code is a separate path | Resolve precise fields/transport; do not emit guessed packet bytes |
| Decoder coexistence | step-reports/03-second-decoder.md | Dual NVIDIA decode plausible; active CarPlay coexistence not established | Revisit only when a second stream/session exists |
| Live evidence availability | captures under ignored research/captures/hondahack-display-path/20260928T152742Z | Factory Navigation, Advanced Meter, Screen Casting snapshots and SHA-256 list saved locally | None for these three states |

Raw evidence, APKs, firmware, forensic images, and sensitive device identifiers are excluded from Git. Sanitized conclusions are recorded in the research and step reports.
# Step 19: the disconnected read-only `/proc` baseline confirms `jmcs` PID `26577`, base `0x4008f000`, 45 mapped `.so` paths, and two process-owned listeners on port 5000. The known generic registration entry points are in `jmcs`; `libcarplay_proxy.so` does not import the device-manager APIs. The listener role and runtime registry winner remain unresolved. Raw `/proc` metadata is in an ignored local capture; derived evidence is in `step-reports/19-jmcs-proc-differential.md`, `research/carplay/jmcs-runtime-sockets.md`, and `research/carplay/jmcs-module-inventory.md`.


## Step 24 — ptrace reader (offline)

`research/tools/jmcs_ptrace_registry_reader/` contains the source, synthetic tests, and r23c ARMv7/API17 build recipe. SHA-256: `1fa1fc980637af5c586b0897ef46ae8c5639c12ac5028ff8d3d0a76e7b672bad`. Tests and static binary audits pass. `process_vm_readv` is closed after its one ENOSYS result. Ptrace live readiness remains NO pending review of single-thread pause, sibling-thread races, signal handling, and detach failure. No live operation occurred. See `research/carplay/ptrace-registry-reader.md`, `step-reports/24-ptrace-registry-reader.md`.
## Step 31 — AirPlay server-info consumer search

`AirPlayCopyServerInfo` (`0x282cd4`) is GLOBAL in `jmcs` `.symtab`, not present in `.dynsym`, and has no ordinary dynamic import relocation. Scanning exact acquired shared objects corresponding to the 45 mapped `.so` modules found no import/export match for it or the related property/display functions. Generic `dlopen`/`dlsym` references and a `/info` string exist in `jmcs`, but no server-info lookup key or handler edge was established. Reverse tracing confirms the existing `_requestSendPlistResponse` → binary-plist → HTTP → `SocketWriteData` → `writev` chain takes `AirPlayReceiverSessionSetup` output, not `AirPlayCopyServerInfo`. Therefore `DISPLAYS_PHONE_FACING=UNKNOWN`, mutation point UNKNOWN, two-hook sufficiency UNKNOWN, offline implementation NO, live test NO. See `step-reports/31-airplay-server-info-consumer.md` and `research/carplay/airplay-server-info-consumers.md`.
## Step 32 — `/info` server-info path recovered

Correcting Step 31: `_connectionHandleMessage` dispatches `/info` to `_requestProcessInfo` (`0x28a018`, edge at `0x28b68e`). That handler calls `AirPlayCopyServerInfo` (`0x282cd4`, `0x28a156`) and passes its exact returned dictionary to `_requestSendPlistResponse` (`0x289f60`, `0x28a19c`). It releases the object at `0x28a1da` after synchronous serialization. `/info` response then goes through `_connectionHandleMessage` → `HTTPConnectionSendResponse` (`0x29dbe4`, `0x28b790`) → `_HTTPConnectionRunStateMachine` → `SocketWriteData` → `writev`. The serializer uses binary plist format `0xc8`. Thus `displays[]` is statically phone-facing and mutable before serialization. No Honda `FeatureKey`/`altScreen`/`viewAreas`/`enabledFeatures` literal or construction was found; modern prior art is not Honda proof. `streamConnectionID` binding and Type-111 ABI remain open. See Step 32 report.
## Step 40C — runtime patch lifecycle (2026-09-29)

- [Step report](step-reports/40c-runtime-patch-lifecycle.md): API-17 source interfaces confirmed; exact Honda kernel behavior and executable runtime unavailable; Step 41 stays NO.
- [Executable memory](research/carplay/honda-executable-memory.md): exact local ELF PT_LOAD data, source/runtime evidence levels, and unresolved W^X lifecycle.
- [I-cache](research/carplay/honda-icache.md): ARM Bionic `cacheflush` interface and upstream half-open range semantics; Honda target effects unknown.
- [Thread rendezvous](research/carplay/honda-thread-rendezvous.md): explains why uncoordinated four-byte patching is unsafe and why no current stop-world mechanism qualifies.
- [Veneer allocation](research/carplay/honda-veneer-allocation.md): exact checked Thumb BL ranges and why arithmetic does not prove an allocatable gap.
- [Runtime lifecycle](research/carplay/honda-runtime-patch-lifecycle.md): API table, evidence classification, failure-order requirements, and implementation boundary.
- Host-only models: `src/claritylink-honda/page_model.py`, `veneer_ranges.py`, `veneer_allocator_model.py`, `rendezvous_model.py`; tests in `tests/honda/test_runtime_safety_models.py`.
# Step 41A evidence

## Step 41C evidence

| Question | Evidence | Conclusion |
|---|---|---|
| Exact jmcs service and imports | `research/carplay/jmcs-init-service.md` | Recovered from boot ramdisk and byte-matched root-startup archive; class main, root:root. |
| Per-service preload seam | `research/carplay/claritylink-load-seam.md` | One `setenv LD_PRELOAD` option is supported without modifying jmcs; no deployment occurred. |
| Secure-execution condition and staging path | Same load-seam note and `step-reports/41c-jmcs-init-service.md` | High-confidence linker support; SELinux/AT_SECURE and staged-library policy remain unknown. |

## Step 41B evidence

| Question | Evidence | Conclusion |
|---|---|---|
| Android 4.2 ARM linker API | `research/runtime/android42-arm-dynamic-linker.md`; tagged `linker/dlfcn.c` | `dladdr` YES; `dl_iterate_phdr` NO on ARM. |
| Honda linker/Bionic | `research/runtime/honda-bionic-dladdr.md` | `libdl.so` export table matches the six tagged ARM names; exact `dladdr` semantics high-confidence, not direct disassembly proof. |
| jmcs startup and dependencies | `research/runtime/jmcs-startup-path.md`; `jmcs-dependency-graph.md` | `/system/bin/linker` runs ET_DYN jmcs; direct dependency list recovered; init service absent from extracted archive. |
| Native loader candidates | `research/runtime/jmcs-dlopen-sites.md`; `jmcs-load-seam-audit.md`; `libcarplay-proxy-load-path.md` | No legitimate existing plugin seam proven; proxy is direct DT_NEEDED but not a loader. |
| Future bounded load change | `research/runtime/minimum-interposer-deployment.md` | Conditional one-line init service preload candidate; exact service file is unknown. |
| Host locator model | `src/claritylink-hook/self_locator.py`, `target_descriptors.py`; `tests/hook/smoke_self_locator.py` | Bounded maps and dladdr-result models; exact hashes/callsite fingerprints; no runtime reads or patches. |

| Question | Evidence | Current conclusion |
|---|---|---|
| Is external privileged maps access required? | `research/runtime/step41-dependency-reassessment.md`; `research/runtime/honda-in-process-location.md` | No as architectural prerequisite once loaded in-process; own-map/API exact target capability remains conditional. |
| What is the Honda executable? | `research/runtime/honda-jmcs-elf-model.md`; prior Step 40 identity report | ARM32 ET_DYN, exact SHA-256 recorded; load-bias formula statically modelable. |
| Is there a Honda load seam? | `research/runtime/honda-native-load-seams.md` | None proven. |
| Does Honda support modern capability tokens / Type111? | `research/carplay/carplay-negotiation-generations.md`; `honda-info-capabilities.md`; `honda-type111-minimum.md` | Legacy `/info` confirmed; R15/token/Type111 response support unknown or partial. |
| Offline validator | `src/claritylink-hook/self_locator.py`; `tests/hook/test_self_locator.py` | Synthetic-only, fail-closed; no runtime or patch capability. |
## Step 41E — Honda init and linker preload behavior (2026-09-30)

| Area | Primary evidence | Finding |
|---|---|---|
| Init service and setenv | `research/deployment/jmcs-init-service.md`, `research/carplay/jmcs-init-service.md` | Exact jmcs service stanza runs root:root, has no LD_PRELOAD, and Honda init has a setenv parser diagnostic |
| Linker fingerprint | `research/runtime/honda-bionic-dladdr.md`, `research/deployment/jmcs-ld-preload.md` | Honda linker hash and LD_PRELOAD/loader strings recorded; no control-flow proof of secure suppression, absolute paths, or failure behavior |
| SELinux/secure execution | `research/deployment/jmcs-secure-exec.md`, `research/carplay/step41d-selinux-load-environment.md` | Policy files absent from inspected archive trees, but active SELinux state/domain and actual AT_SECURE remain UNKNOWN |
| Candidate path | `research/deployment/library-staging-paths.md` | `/data/local/tmp` is 0771 shell:shell and best candidate; executable-map permission unproven |
| Decision | `step-reports/41e-init-linker-preload-behavior.md`, `research/deployment/noop-interposer-plan.md` | LD_PRELOAD is a plausible secondary seam; boot ramdisk change required; no-op test NOT READY |
## Step 41F — Honda linker preload fingerprint (2026-09-30)

| Area | Primary evidence | Finding |
|---|---|---|
| Exact linker | `step-reports/41f-honda-linker-preload-fingerprint.md`, `research/runtime/honda-bionic-dladdr.md` | Archived linker hash matches Step 41B; ELF32 ARM ET_DYN; preload/path/error strings and data pointers present |
| Behavioral comparison | `research/deployment/honda-linker-ld-preload.md` | Exact Honda secure check, absolute path handling, separators, fatal-load behavior, and ctor order remain UNKNOWN; no local matching AOSP source checkout |
| Secure exec | `research/deployment/jmcs-secure-exec.md` | Root-to-root/no-setid metadata suggests AT_SECURE=0 absent LSM decision; actual state unknown |
| `/data` mount and candidate | Historical capture `research/captures/20260925T150706Z-capabilities/capability-survey/cat-_proc_mounts.txt`; `research/deployment/library-staging-paths.md` | `/data` was `rw,nosuid,nodev` without `noexec`; SELinux and executable mmap remain unknown, risk MEDIUM |
| Decision | `step-reports/41f-honda-linker-preload-fingerprint.md`, `research/deployment/noop-interposer-plan.md` | LD_PRELOAD seam remains PLAUSIBLE_SECONDARY; no-op load and Type111 not ready |
## Step 41G — offline linker lab/seam decision (2026-09-30)

| Area | Primary evidence | Finding |
|---|---|---|
| Lab feasibility | `step-reports/41g-offline-linker-behavior-lab.md` | No qemu-arm user-mode, container runtime, or ready ARM guest; system QEMU alone is insufficient; no proprietary binary executed |
| Targeted static pass | Same report; archived linker hash and Capstone/llvm-objdump | Preload strings/data confirmed; control flow to getenv/parser/secure path/fatal failure not resolved; direct helper calls not found in bounded scan |
| Data mapping context | Same report; historical `/proc/mounts` capture | `/data` was rw,nosuid,nodev without noexec; SELinux/mmap still unknown, MEDIUM risk |
| Seam decision | `research/deployment/next-load-seam-options.md`, `research/deployment/noop-interposer-plan.md` | LD_PRELOAD is UNKNOWN/parked; no-op and Type111 not ready; next study is ExternalDisplay/CarPlayService companion path |
# Step 42G — host decoder

| Question | Evidence | Conclusion |
|---|---|---|
| Host decode adapter and bounds | `src/claritylink-sim/host_h264_decoder.py`; `tests/sim/test_host_h264_decoder.py` | Optional FFmpeg CLI path accepts bounded Annex-B with SPS/PPS and returns a validated one-frame RGBA result; mock process test verifies the adapter boundary. |
| Synthetic H.264 source | Same decoder module; `research/simulator/host-h264-decode-stage.md` | In-memory FFmpeg/libx264 test-pattern generator added; no media committed. Actual generation was unavailable here. |
| Current replay decode status | `src/claritylink-sim/synthetic_type111_replay.py`; `demo/type111/replay-data.json` | Existing replay payload is parser-shaped, not valid H.264; it is never decoded and fallback is labeled. |
| Host tool availability | Step 42G report | No FFmpeg/PyAV/OpenCV/imageio decoder on this host; real decode test skipped explicitly. Live integration readiness unchanged. |

## Step 42I — actual synthetic decode

| Question | Evidence | Conclusion |
|---|---|---|
| Host tools | `step-reports/42i-real-synthetic-h264-decode.md`; `probe_ffmpeg_capabilities()` | FFmpeg/ffprobe 9.0.2, libx264, H.264 decoder, and RGBA output available on this Mac; no install needed. |
| Real synthetic encode/decode | `tests/sim/test_host_h264_decoder.py`; in-memory test pattern | Actual 320×180 synthetic pattern encoded to Annex-B H.264 and decoded; 230,400-byte RGBA frame validated. |
| Renderer handoff | Same test; `src/claritylink-sim/export_visual_demo.py --decode-synthetic-h264` | Actual decoded frame reached mock Display 1; generated JSON records `HOST-DECODED SYNTHETIC H264`. |
| Honda/CarPlay meaning | `research/simulator/host-h264-decode-stage.md` | Independent synthetic test only; parser fixture is not decoded; Type111/Honda and live ExternalDisplay remain unproven. |

## Step 42H — synthetic H.264 validation

| Question | Evidence | Conclusion |
|---|---|---|
| FFmpeg / encoder / decoder availability | `step-reports/42h-ffmpeg-synthetic-h264-validation.md`; `probe_ffmpeg_capabilities()` | FFmpeg, libx264, H.264 decoder, and RGBA output are unavailable; no installation attempted. |
| Synthetic media encode/decode | `tests/sim/test_host_h264_decoder.py` | Real test skips explicitly when FFmpeg is absent; no media was generated in this run. |
| Renderer handoff | Same test; `research/display/type111-renderer-handoff-contract.md` | Fake-process RGBA adapter check passes; actual decoded-frame submission remains skipped. |
| Twin and live readiness | `PROJECT_STATE.md`; Step 42H report | Offline twin remains ready; live Type111, jmcs no-op, and ExternalDisplay rendering remain NOT READY. |

## Step 42K — actual decoded pixels in visual twin (2026-09-30)

| Area | Evidence | Finding |
|---|---|---|
| Source path | `src/claritylink-sim/synthetic_screenstream_fixture.py`; `src/claritylink-sim/export_visual_demo.py` | The PNG is generated from the exact `DecodedFrame` retained as accepted by the ScreenStream pipeline's Display 1 mock; no parallel browser/media frame source is used |
| Pixel provenance | `demo/type111/replay-data.json`; `demo/type111/runtime/` (ignored); `tests/integration/test_visual_frame_artifact.py` | Metadata stores dimensions, RGBA byte count, raw-pixel SHA-256, and `SYNTHETIC_TEST_VALUE`; test decodes PNG IDAT and verifies pixel equality. Generated PNG stays ignored |
| UI/fallback | `demo/type111/index.html`; `demo/type111/README.md` | Hypothetical mode displays the frame only after loading at matching dimensions; strict Honda mode stays empty; missing asset falls back to an identified schematic |
| Invariants/readiness | `tests/sim/test_synthetic_screenstream_fixture.py`; `step-reports/42k-actual-decoded-frame-visual-demo.md` | Type110/audio isolation and stale-output clearing pass. This remains synthetic/mock evidence; live Type111, jmcs integration and ExternalDisplay rendering are NOT READY |

## Step 42J — valid synthetic H.264 through ScreenStream model

| Area | Primary evidence | Finding |
|---|---|---|
| Synthetic media and NAL extraction | `src/claritylink-sim/synthetic_screenstream_fixture.py`; `tests/sim/test_synthetic_screenstream_fixture.py` | FFmpeg 9.0.2/libx264 generated 7,877 in-memory Annex-B bytes; NAL types 5/6/7/8, one SPS, one PPS, three VCL NALs. No media files retained. |
| Config and packet model | Same fixture module and tests | Synthetic avcC-style config is 39 bytes with 4-byte NAL length; AVCC frame body 7,237 bytes; modeled opcode 1/0 packets 167/7,365 bytes including 128-byte headers. Crypto mode is `PLAINTEXT_SYNTHETIC`. |
| Parse/decode/render | Same tests; `demo/type111/replay-data.json` `screenstream_validation` | Receiver parser emitted config and Annex-B frame; FFmpeg decoded 320×180 to 230,400 RGBA bytes and mock Display 1 accepted the frame. Visual status is `HOST-DECODED SYNTHETIC H264 VIA SCREENSTREAM FIXTURE`. |
| Failure isolation and evidence | New fixture tests; `research/carplay/type111-unknown-register.md` | Missing/malformed config, unsupported width, malformed AVCC, bad H.264, renderer rejection, incomplete bodies, and unknown opcodes are exercised; Honda Type111 crypto/schema/correlation and ExternalDisplay remain UNKNOWN. All live gates remain NOT READY. |
# External secondary-screen prior art — reviewed 2026-09-30

The sources below are `EXTERNAL_PRIOR_ART`. They describe Apple platform behavior or other receivers and do **not** establish Honda MY16ADA support. The source-pinned research and xcertplay/Honda field comparison are in [docs/research/carplay-altscreen-prior-art.md](docs/research/carplay-altscreen-prior-art.md).

| Evidence item | Source and pinned revision | Classification | Demonstrates | Does not prove about Honda |
|---|---|---|---|---|
| Apple secondary-screen architecture | [WWDC 2019 session 252](https://developer.apple.com/videos/play/wwdc2019/252/), 2019 | `EXTERNAL_PRIOR_ART` | iOS 13-era independent H.264 streams for vehicle displays, including map/maneuver cluster content; R15 context. | Honda receiver support, Type111 schema, or phone negotiation. |
| Apple simulator cluster display | [WWDC 2022 session 10016](https://developer.apple.com/videos/play/wwdc2022/10016/) and [CarPlay Simulator docs](https://developer.apple.com/documentation/carplay/using-the-carplay-simulator) | `EXTERNAL_PRIOR_ART` | App/simulator workflow with an instrument-cluster display beside primary CarPlay. | Honda wire behavior or production receiver capability. |
| xcertplay display descriptors | [shilapi/xcertplay `de9647f4bdfb1be356bed4cac0519400473712a6`](https://github.com/shilapi/xcertplay/commit/de9647f4bdfb1be356bed4cac0519400473712a6) | `EXTERNAL_PRIOR_ART` | Source builds main/alternate descriptor entries with types 110/111, separate UUID constants, dimensions, features, view areas, and optional UI context. | That Honda emits type 111, viewAreas, initialURL, or accepts a second descriptor. Honda comparison is in the linked research doc. |
| MHI2 Type111 implementation | [harman-f/mhi2_altscreen_carplay `c2f811f1a5c84dae3a62f4cf9b4a9e65fc3f7b3c`](https://github.com/harman-f/mhi2_altscreen_carplay/commit/c2f811f1a5c84dae3a62f4cf9b4a9e65fc3f7b3c) | `EXTERNAL_PRIOR_ART` | Its project reports a vehicle Stream-111 PoC and documents stock-first Setup, a separately owned Type111 listener, descriptor cloning, and target-specific hooks. | Honda offsets, ABI, load seam, session objects, crypto, or Type111 acceptance. |
| MHI2 session/crypto prior art | Same pinned MHI2 commit; `docs/research/MU1440_GEN2_HOOK_MAP.md`, `docs/research/STREAM111_PROTOCOL.md` | `EXTERNAL_PRIOR_ART` | MHI2-specific secondary stream connection identity/security handling and independent lifecycle. | That Honda Type110 KDF is valid for Type111. Honda Type110 uses master material plus streamConnectionID; Honda Type111 remains `UNKNOWN`. |
| MHI2 UI/ViewArea prior art | Same pinned MHI2 commit; `docs/research/IOS27_SENDER_LIFECYCLE.md` | `EXTERNAL_PRIOR_ART` | Sender-analysis for a stated iOS 27.2 beta build separates UI ownership commands, ViewArea changes, and media transport. | Honda implements those commands or URL strings, or that they are stable public interfaces. |
| CPC200 navigation-screen prior art | [lvalen91/CPC200-CCPA_resources `e3e5d005552d3fa6f264634b377d30b0794dd1eb`](https://github.com/lvalen91/CPC200-CCPA_resources/commit/e3e5d005552d3fa6f264634b377d30b0794dd1eb), `documentation/02_Protocol_Reference/video_protocol.md` | `EXTERNAL_PRIOR_ART` | CPC200-specific navigation geometry/video and focus-controlled flow in its wired adapter documentation. | Honda uses CPC200 protocol or that capability advertisement alone causes iOS to open a secondary stream. |

Honda-specific source notes remain separately indexed below; no external project evidence has been relabeled as Honda-confirmed.
# Step 43E — Honda post-Setup / pre-serialization seam (2026-09-30)

| Area | Primary evidence | Finding |
|---|---|---|
| Response lifetime/ownership | `research/carplay/honda-post-setup-response-seam.md`; `honda-response-ownership.md`; `honda-response-serializer.md` | Setup publishes the response +1; caller passes same object to synchronous binary-plist serialization and releases it afterward. Request/session remain in caller context. |
| Mutability boundary | Same seam note; Setup response construction at `0x28557e`; `_AddResponseStream` at `0x284db8` | Response dictionary and `streams` array are mutable during stock construction. Caller-side post-return mutation remains `INDIRECT_CANDIDATE`, not runtime-proven. |
| Detection/rollback | Same seam note; `src/claritylink-negotiation/setup_transaction.py`; `tests/negotiation/test_setup_contract.py` | `ORIGINAL_REQUEST_AFTER_STOCK` is supported by static flow; synthetic failure model preserves stock values and rolls project state back. No Honda Type111 semantics claimed. |
| External comparison | `research/carplay/setup-stream-identity-prior-art.md` | MHI2 stock-first clone/append is `EXTERNAL_PRIOR_ART` only; hook safety and schema are not portable facts. |
| Decision | `step-reports/43e-post-setup-response-seam.md`; `NEXT_ACTION.md` | `SAFE_STATIC_CANDIDATE`; implementation/readiness gates remain NO; next task is exact liveness and cleanup proof. |

# Step 43F — caller liveness and CF cleanup (2026-09-30)

| Area | Primary evidence | Finding |
|---|---|---|
| Caller instruction liveness | `research/carplay/honda-post-setup-caller-liveness.md`; `jmcs` SHA-256 `cbc7ba881648fb8ffdfcc4c1100a028345c37134a2ae3b9dff7d76572851c232` | Request dictionary `[sp+0x1c]`, session reload `[r10+0xf4]`, responseOut `[sp+0x54]`, HTTP request `r6`, connection `r4`, and status `[sp+0x50]` remain available through direct serializer call at `0x28afba`. |
| Serializer and cleanup | Same note; `_requestSendPlistResponse` `0x289f60`; common release `0x28b052` | Direct same Setup response is synchronously serialized; caller releases after helper returns. Later HTTP state-machine write is asynchronous/later. |
| Mutable CF objects | Same note; Setup `CFDictionaryCreateMutable` `0x28557e`; `_AddResponseStream` `0x284db8` | Stock response and streams array are `CONFIRMED_MUTABLE` by creation/append path. Callback identities/precise retain accounting and caller-side race safety remain unresolved. |
| Callout/failure model | Same note; `step-reports/43f-caller-liveness-cf-cleanup.md` | Structural insertion interval found; callout requires trampoline; cleanup after serializer/queue failure is partial. |
| Test environment/readiness | `docs/development/testing.md`; `requirements-test.txt`; [Offline CI run](https://github.com/bmreyes25/ClarityLink/actions/runs/36813310742); `NEXT_ACTION.md` | Local pytest unavailable although setup instructions exist; CI passed on starting HEAD. Seam implementation design remains `NEEDS_MORE_STATIC_PROOF`; no live gate advanced. |
# Step 43G — Honda CF callback and failure cleanup

| Area | Primary evidence | Finding |
|---|---|---|
| CFL callback tables | `research/carplay/honda-cf-callback-ownership.md`; identity-verified `jmcs` ELF symbol/data references | Array and dictionary callback table symbols/wrappers are identified, but Setup's dictionary callback arguments and Type110 entry callback/release ledger remain unresolved; table presence is not call-site proof. `HONDA_INDIRECT_CANDIDATE`. |
| Serializer failure | Same research note; `_requestSendPlistResponse` and caller cleanup path | Property-list creation failure returns through common cleanup, releasing response and request. Body setter can fail after partial HTTP-message mutation. `HONDA_CONFIRMED` path, partial body-state implications. |
| HTTP queue/write failure | Same note; `HTTPConnectionSendResponse` → state machine → `SocketWriteData`/`writev` | CF graph is released before queuing; later send failure cannot mutate it. Connection callback's session/project resource cleanup is not resolved. `HONDA_CONFIRMED` send path; cleanup `HONDA_UNKNOWN`. |
| Race/readiness | Step 43G report | No response escape is seen in inspected caller path before serialization, but thread exclusivity is unproven. Race classified `NO_STATIC_EVIDENCE`; seam remains `NEEDS_MORE_STATIC_PROOF`. |

## Step 43H — CF callback fingerprint and post-serialization cleanup

| Evidence item | Source | Finding / classification |
|---|---|---|
| Exact Setup callback arguments | `research/native/jmcs/focused-annotated.txt`; Step 43H report | Setup response dictionary and `streams` callback pointers remain unresolved. Named tables alone are not call-site proof. |
| Positive call-site controls | Same disassembly | `/info` dictionary at `0x287af8` passes named CFType key/value tables; global screen array at `0x2a18ae` passes named CFType array table. These are separate objects. |
| Type110 ownership | `research/carplay/honda-cf-callback-ownership.md` | Entry retain/release ledger and response-to-streams retaining edge remain unknown/partial. |
| Serialization boundary | `research/carplay/honda-post-setup-caller-liveness.md` | Response graph is released after synchronous serialization; later network failure does not need CF graph rollback. Project stream cleanup edge is unknown. |
| Readiness / next | [Step 43H report](step-reports/43h-cf-callback-fingerprint.md); `NEXT_ACTION.md` | `NEEDS_MORE_STATIC_PROOF`; all implementation/live gates NO; LD_PRELOAD PARKED. Next: recover exact Setup callback arguments and session cleanup callback. |
# Step 43I — Honda session delegate and finalizer lifecycle (offline)

| Evidence item | Source | Finding / classification |
|---|---|---|
| Artifact identity and address mapping | jmcs SHA-256 `cbc7ba881648fb8ffdfcc4c1100a028345c37134a2ae3b9dff7d76572851c232`; `tools/elf_va_map.py`; Xcode `llvm-objdump` | `HONDA_CONFIRMED`: verified image; ELF VA/literal mapping and Thumb normalization used. |
| Session runtime class/finalizer | class table `0x3427d4`; `AirPlayReceiverSessionGetTypeID` `0x284e28`; `_Finalize` `0x284d24` | `HONDA_CONFIRMED`: registered CF runtime object; callback at session `+0x20` receives session and context before remaining resource teardown. |
| Delegate replacement and callback target | `AirPlayReceiverSessionSetDelegate` `0x285040`; `_AirPlayHandleSessionCreated` `0xaf04c`; `_AirPlayHandleSessionFinalized` `0xae654` | `HONDA_CONFIRMED`: 44-byte whole-table copy; existing non-null finalizer callback at slot `+0x0c`; server session-created wiring proven. |
| Request-aware stream teardown | `AirPlayReceiverSessionTearDown` `0x2852ec`; `AirPlayReceiverSessionPlatformControl` `0x28cd88` | `HONDA_CONFIRMED`: passes `tearDownStreams` and request; parser distinguishes 100/101/110. Does not prove Type111 or project callback. |
| Project child and readiness | `research/carplay/honda-project-child-lifecycle-contract.md` | Finalizer is a candidate; request-aware child attachment unknown; exact-once contract remains synthetic; project model needs more static proof. |
| External prior art | `docs/research/airplay-session-lifecycle-prior-art.md` | `EXTERNAL_PRIOR_ART` only; no ABI equivalence inferred. |
| Report/tests | `step-reports/43i-honda-session-delegate-finalizer.md`; `NEXT_ACTION.md` | See report for test results and gates. |

## Step 43J — platform lifecycle seam

| Evidence item | Source | Finding / classification |
|---|---|---|
| R11B structural fingerprint | Honda delegate disassembly; pinned R11B prior art; `research/carplay/honda-session-delegate-lifecycle.md` | All 11 offsets and populated/null slots align; STRONG structural fingerprint only, no Honda ABI names/provenance inferred. |
| Request-aware teardown routing | PlatformControl `0x28cd88`, branch `0x28cfe0–0x28d2e2`; [platform lifecycle trace](research/carplay/honda-platform-lifecycle-seam.md) | `tearDownStreams` handles typed streams internally. Does not call delegate control at session+0x24. Types 100/101/110 recognized; Type111 unknown/ignored. |
| Full-session cleanup | `_Finalize` `0x284d24` calls PlatformFinalize `0x28cd60`; symbol/call audit | One direct call per finalizer invocation; tolerates no platform pointer; null-request `_TearDownStreams`, free and clear. HTTP/earlier teardown independent. |
| Synthetic registry/adapter | `src/carplay-session-model/project_lifecycle.py`; focused tests; [child contract](research/carplay/honda-project-child-lifecycle-contract.md) | Offline-only, idempotent child cleanup keyed by `(session,generation)`; stock called once with unchanged request; not an installable Honda extension. |
| Readiness | [Step 43J](step-reports/43j-platform-lifecycle-seam.md); `NEXT_ACTION.md` | Child lifecycle READY_FOR_OFFLINE_PROTOTYPE; post-Setup seam and safe platform integration remain NEEDS_MORE_STATIC_PROOF; live gates NOT READY; LD_PRELOAD PARKED. |

## Step 43K — offline project-session registry

| Evidence item | Source | Finding / classification |
|---|---|---|
| Opaque identity/generation and state machine | `src/carplay-session-model/project_lifecycle.py` | `OFFLINE_PROJECT_IMPLEMENTATION`: PREPARING/PREPARED/ACTIVE/STOPPING/STOPPED, transaction-owned precommit resources, registry ownership after commit, exact generation lookup. |
| Stock lifecycle adapters | Same module; `tests/carplay-session-model/test_project_lifecycle.py` | Synthetic adapter invokes stock once, passes unchanged object arguments, preserves stock result, and performs Type111 cleanup after stock. Finalization detaches project state before stock. No Honda execution or integration. |
| Concurrency/failure coverage | Focused lifecycle tests | 25 focused passed; EOF/teardown/finalize, prepare/finalize, rollback/finalize, pointer reuse and event-sequence invariants are synthetic only. |
| Related groups and full suite | pytest and `tools/run_tests.sh` | Related groups 116 passed; full suite 266 passed, 4 skipped; capture replay unavailable. |
| Step 43L boundary | [Honda integration contract](research/carplay/honda-post-setup-integration-contract.md); `NEXT_ACTION.md` | Exact successful Setup interval, object lifetimes/ownership, response mutation/rollback, serializer outcome, and commit point still require Honda static proof. JMCS integration/live gates remain closed. |
## Step 43L — post-Setup transaction seam

| Evidence | Result / boundary |
|---|---|
| Setup return and success path | Hash-matched `jmcs`: Setup BL `0x28af72`; status check `0x28af76–0x28af7c`; success context through `CFObjectSetProperty` `0x28afae`; same output response to serializer `0x28afba`; release `0x28b052`. Structural interval is proven; safe injected callout is not. |
| Serializer | `_requestSendPlistResponse` `0x289f60`: synchronous property-list CFData (`0xc8`), byte/length extraction, HTTPMessageSetBody `0x29d01c`, status 200/500 and statusOut. Serializer success at caller `0x28afbe` is local readiness, not receipt. |
| Rollback | Public CF array API includes count/get/create-copy/mutable/append, no public indexed remove/set wrapper found. Use LAST_MUTATION candidate; selective append/remove rollback is unsupported. |
| Response transaction | Same Honda response object retained; type-based stream lookup; pre-serializer fail-open conditional; serializer failure does not promise Type110 delivery. Child commit candidate `0x28afbe`; cleanup subscription and callout safety unproven. |
| Status | `POST_SETUP_TRANSACTION_MODEL: PARTIAL`; `JMCS integration design: NOT READY`; report `step-reports/43l-post-setup-transaction-seam.md`. |
## Step 43L.1 — callout safety and cleanup reachability

| Evidence | Finding |
|---|---|
| Caller ABI and callout candidates | `research/carplay/honda-post-setup-callout-safety.md`: 8-byte aligned caller frame; request `[sp+0x1c]`, response `[sp+0x54]`, status `[sp+0x50]`, session `[r10+0xf4]`; `0x28afb2` is structurally best, but occupied and CANDIDATE_ONLY. No helper callout safety or spare instruction slot is proven. |
| Serializer result | `0x289ff8` returns `0xc8` on body success, `0x1f4` on helper failure; statusOut records `HTTPMessageSetBody`/error result. RESPONSE_READY predicate is `r0==0xc8 && statusOut==0`. |
| Cleanup reachability | `research/carplay/honda-project-child-cleanup-reachability.md`: HTTP close conditionally tears down non-null session; Honda session finalization is proven but project child cannot reach it through a supported subscription. Response graph is released before network delivery. |
| Generation guard | `project-session-registry.md`: generation and idempotent cleanup exist synthetically; watchdog timing/renewal and Honda event hookup are unknown. Required; model PARTIAL. |
| Decision | [43L.1 report](step-reports/43l1-callout-safety-cleanup-reachability.md): CALLOUT CANDIDATE_ONLY; ABI PARTIAL; cleanup PARTIAL/NOT_PROVEN; integration NEEDS_MORE_STATIC_PROOF. |

## Step 43L.2 — finalizer extension and generation guard

| Evidence | Finding |
|---|---|
| Finalizer callback | [`honda-session-finalizer-dataflow.md`](research/carplay/honda-session-finalizer-dataflow.md): `_Finalize` calls the Honda per-session finalizer with session/context; finalizer emits interface event 2 (`MC_DEV_CARPLAY_SESSION_DESTROYED`) through a global callback. |
| Registration and chaining | [`honda-session-finalizer-registration.md`](research/carplay/honda-session-finalizer-registration.md): both session delegate and app interface callback setters replace fixed-size whole records; no multi-subscriber dispatch or safe session-addressable chain found. |
| Cleanup consequence | [`honda-project-child-cleanup-reachability.md`](research/carplay/honda-project-child-cleanup-reachability.md): pre-session delivery failure does not prove finalizer execution; finalizer is optional cleanup signal. |
| Project guard | [`honda-generation-guard-model.md`](research/carplay/honda-generation-guard-model.md), `project_lifecycle.py`: exact generation supersession, configurable renewable lease/reaping, idempotent cleanup; synthetic only. |
| Decision | [43L.2 audit](step-reports/43l2-session-finalizer-extension-audit.md): NO_SUPPORTED_EXTENSION; guard COMPLETE offline; `LIFECYCLE_MODEL_READY_CALLOUT_UNRESOLVED`; runtime integration not ready. |
