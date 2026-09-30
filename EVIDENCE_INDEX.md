## Step 40E — parked read-only Honda runtime preflight (2026-09-29)

| Area | Primary evidence | Finding |
|---|---|---|
| Read-only collector | `tools/honda-readonly-preflight/collector.py`, `README.md` | Fixed read-only operations, explicit parked/disconnected gates, one-device and MY16ADA/kernel identity guards, no arbitrary command/upload/write path, per-command timeout/output cap, host-only raw storage |
| Host parsers/analyzer | `tools/honda-readonly-preflight/parsers.py`, `analyze.py`, `tests/honda/test_readonly_preflight.py` | Synthetic maps/smaps/status/signal/task/network/load-bias/gap/privacy tests; no ADB dependency |
| Live attempt | `research/platform/honda-live-runtime.md`, `step-reports/40e-readonly-runtime-preflight.md` | Host ADB listed one authorized target; first read-only `uname -a` failed `error: closed`; no phase capture or Honda runtime facts |
| Hook/runtime gates | `research/carplay/honda-runtime-addressing.md`, `honda-veneer-allocation.md`, `honda-thread-rendezvous.md`, `honda-runtime-patch-lifecycle.md`, `honda-hook-safety.md` | No live addresses/gaps/signal/thread data; Step 40F and Step 41 remain NO |
| Verification/review | Step 40E report | 19 focused tests; Honda 74/1 skipped, interposer 14, transport+negotiation 47 + 31 subtests, renderer 8; ECC skills used, independent reviewer unavailable |

## Step 40D — kernel provenance and API-17 ARM runtime (2026-09-29)

| Area | Primary evidence | Finding |
|---|---|---|
| Official source | `research/platform/honda-ada01-source.md` | Honda/Panasonic ADA01 archive SHA-256 recorded; safe inventory/extraction; Linux 3.4.108 generic Tegra, no VCM30T30; related source only |
| Target kernel | `research/platform/honda-kernel-provenance.md`, `honda-kernel-config.md` | Forensic copy hash recorded; exact target 3.1.10+; modules corroborate SMP/preempt/ARMv7; config and VM page size unknown |
| API 17 ARM image | `research/platform/api17-arm-runtime.md` | Official image hash verified; Google emulator rejects ARM in both engines; generic QEMU lacks Goldfish; no guest tests |
| Runtime gate | `research/carplay/honda-executable-memory.md`, `honda-icache.md`, `honda-thread-rendezvous.md`, `honda-runtime-patch-lifecycle.md` | No RX/RW/cache/Thumb/veneer/signal/futex/rendezvous runtime proof; Step 41 NO; Step 40E read-only preflight is next |
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
