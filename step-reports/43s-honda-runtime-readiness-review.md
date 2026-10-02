# Step 43S — Honda runtime attachment and Type111 negotiation readiness review

**Decision: `NO_GO`.** Keep all Honda runtime/deployment paths disabled. The offline model is coherent, but the evidence does not establish a safe, narrowly bounded live attachment or real listener contract. This review authorizes no vehicle action.

## Starting point, scope, and boundaries

- Requested and verified starting HEAD: `5abb244fdeb7bf652cb2982991cb04c4fc4a0045` (`main`, synchronized with `origin/main`, clean worktree).
- The exact reference ELF is preserved at `extracted/system/system/bin/jmcs`; a second copy at `extracted/system-vendor/system/bin/jmcs` has the same SHA-256.
- Work was offline: no ADB, Honda connection, process command, listener socket, patch, install, partition/file/memory write, USB payload, CAN operation, or live negotiation was performed.
- 43S adds a synthetic presentation model and this readiness report. It does not emit trampoline code or patch bytes.

## External research update

Current public evidence materially strengthens the architecture while remaining outside the Honda evidence boundary:

- The MHI2 AltScreen project reports a 2026-09-29 in-vehicle proof of moving Type-111 navigation in a Škoda Virtual Cockpit for Apple Maps, Google Maps, and Waze. It describes a dedicated Auxiliary/ScreenAlt path and explicitly distinguishes it from mirroring the center display. It also reports that navigation ownership changes do not generally require Type-111 teardown, `suggestUI` and `showUI` are distinct, and ViewArea changes are handled within an existing stream. [MHI2 AltScreen project](https://github.com/harman-f/mhi2_altscreen_carplay/blob/main/README.md)
- The MHI2Q AltScreen release describes a vehicle-validated native CarPlay secondary view with the main display still available; its stated validation scope is Audi MHI2Q / China-region firmware, not Honda. [MHI2Q AltScreen project](https://github.com/yuedizhibo/MHI2Q-CarPlay-AltScreen/blob/main/README_EN.md)
- Current public iOS 27 reverse-engineering notes continue to identify `altScreen`, `viewAreas`, and `altScreenURLs`. This is `EXTERNAL_PRIOR_ART`; it independently agrees structurally with the 43P phone observation but does not replace it. [CarLink Linux capability notes](https://github.com/lvalen91/carlink_linux/blob/main/docs/CARPLAY_CAPABILITIES.md)
- Apple documents instrument-cluster navigation scenes and route guidance in instrument clusters. This validates the general CarPlay product architecture, not this protocol implementation or Honda acceptance. [Apple CarPlay developer page](https://developer.apple.com/carplay/), [instrument-cluster scene key](https://developer.apple.com/documentation/bundleresources/information-property-list/uiapplicationscenemanifest/cpsupportsinstrumentclusternavigationscene)
- Honda's 2018 Clarity documentation remains ordinary CarPlay on the 8-inch center display. No new public Honda MY16ADA/Clarity Type111 acceptance, security, listener ABI, or media evidence was found. External MHI2/MHI2Q findings remain `EXTERNAL_PHYSICAL_VALIDATION` / `EXTERNAL_PRIOR_ART`, never `HONDA_CONFIRMED`.

The key architecture consequence is enforced in the new synthetic model: presentation ownership, ViewArea/SafeArea, and keyframe refresh may change while the same transport generation remains active. A new generation is reserved for actual transport/session events such as fresh SETUP, changed stream ID, socket death, or teardown. The 43Q-B restart machinery remains appropriate for those events, not as a universal UI recovery path.

## Readiness by plane

| Plane | Offline maturity | Honda runtime readiness | Main unresolved items |
|---|---|---|---|
| Negotiation | `LAB_SYNTHETIC_CONFIRMED`: 43R parses SETUP, prepares an exact B generation, reserves a deterministic fake listener, appends only `{type:111,dataPort:P}`, calls the stock serializer once, and commits only on Honda's local success predicate. | **Not ready** | Honda acceptance of Type111 response, actual mutation callout safety, real listener ownership/order and phone behavior. |
| Media | 43Q-A/B provide synthetic independent state, parser/crypto branch fixtures, generation ownership, and stale-callback rejection. | **Not ready** | Honda Type111 framing/security and ScreenStream compatibility are `HONDA_UNKNOWN`; no real accepted socket or decode. Unknown/unsupported security must close the accepted socket and retire only that B generation, without trying guessed AES or ChaCha. |
| Control / presentation | 43P confirms four `suggestUI` events on the tested phone; synthetic state model now represents `suggestUI`, optional `showUI`/`stopUI`, `forceKeyFrame`, ViewArea and SafeArea changes without replacing generation B. | **Not ready** | Current-phone behavior of `showUI`, `stopUI`, `forceKeyFrame`; Honda control semantics/UUID ownership; valid Honda ViewArea/SafeArea and physical aperture. |

### Control-plane evidence matrix

| Item | Project evidence | Classification / status |
|---|---|---|
| `suggestUI` | Four events in 43P; no recorded target UUID or proven Honda semantics | `CURRENT_IOS_LAB_CONFIRMED` as event presence only |
| `showUI`, `stopUI` | Not observed in 43P; described by external implementation work | `EXTERNAL_PRIOR_ART`; current phone and Honda unknown |
| `forceKeyFrame` | Not observed in 43P; prior source studies concern other platforms | `EXTERNAL_PRIOR_ART`; current phone and Honda unknown |
| UI target UUID / AltScreen URL role | External structures exist; Honda-compatible values not established | `EXTERNAL_PRIOR_ART`; Honda unknown |
| ViewArea / SafeArea | 43P saw viewAreas structurally; synthetic PlayPort geometry only | phone structure `CURRENT_IOS_LAB_CONFIRMED`; actual Honda geometry unknown |
| Ownership/provider switch | MHI2 reports same-stream changes; no 43P provider transition observation | `EXTERNAL_PHYSICAL_VALIDATION`; synthetic transition supported |
| Presentation recovery | Offline model changes controls/layout/refresh on same active generation | `LAB_SYNTHETIC_CONFIRMED` only |

## Exact Honda binary and callsite audit

Independent offline revalidation against the preserved ELF succeeded through `tools/jmcs_integration/callsite_plan.py` and its artifact-backed tests:

- Whole-file SHA-256: `cbc7ba881648fb8ffdfcc4c1100a028345c37134a2ae3b9dff7d76572851c232` (both preserved copies).
- ELF: 32-bit little-endian `EM_ARM` (`40`), `ET_DYN`, EABI version 5, Thumb code.
- `_connectionHandleMessage`: `0x28a30c`; `_requestSendPlistResponse`: `0x289f60`.
- Direct Thumb BL callsite: `0x28afba`; bytes `fe f7 d1 ff`; decoded target `0x289f60`; continuation `0x28afbe`; original Thumb-tagged LR `0x28afbf`.
- Callsite context at `0x28afb2` and caller prologue at `0x28a30c` match the pinned bytes and SHA-256 fingerprints in the 43N planner/report. The prologue pushes `r4-r11,lr` then subtracts `0x2b4`, a total `0x2d8` frame delta. Under AAPCS32 8-byte-aligned entry SP, callsite SP remains 8-byte aligned.
- Caller stages connection/message/response/statusOut in `r0-r3`; parsed request `[sp+0x1c]`, `statusOut [sp+0x50]`, response `[sp+0x54]`, and session `[r10+0xf4]` remain live. The stock helper's local success is `r0==0xc8 && statusOut==0`.
- The planner rejects a wrong full-file hash before instruction analysis and checks expected bytes, decoded target, continuation, surrounding context, and prologue. It emits a JSON report only.

This independently satisfies the static identity and callsite gates for the preserved artifact. It does not prove a live loaded mapping, runtime installation mechanism, or safe mutation/callout.

## Trampoline / ABI audit

The synthetic 43N contract models the intended path: save caller LR/state; bounded preparation; restore `r0-r3`; call the stock serializer once with an adapter-local LR; capture stock `r0` and `statusOut`; perform generation-bound completion; restore caller LR/SP and return to `0x28afbe`. It preserves `r4-r11`, SP, and serializer result; it treats `r12` and flags as caller-saved because the observed continuation does not consume them. Prepare failure delegates unchanged to stock once; post-hook failure cannot alter returned status/result.

**This is not an executable trampoline ABI proof.** There is no emitted adapter machine code, relocated BL/veneer implementation, or runtime proof for argument-pointer lifetime, reentrancy, concurrent SETUP calls, or adapter crash behavior. `G5` therefore fails. Before any live attachment, the smallest offline follow-up must produce machine-code/ARM-emulator proof for the exact shim shape, including statusOut pointer behavior, stack/register restoration, one serializer call, exception/fault containment, and return to the original continuation. It must not patch or deploy Honda.

## No-Type111 path and 43R binding

43R's deterministic model keeps a request without Type111 outside B-generation/listener preparation, leaves stock response entries unchanged, and invokes the stock serializer once. Unknown/malformed project inputs fall back to the stock response and do not enter long-lived media lifecycle. Type111 response addition is narrowly `{type:111,dataPort:P}`; no prior-art capability/UUID/geometry fields leak in. Serializer local success is required before activation; Type110 stays outside Type111 child ownership.

This proves offline contract behavior, not that a future binary adapter can safely inspect the parsed request at `0x28afba`; that request is not in `r0-r3` at the serializer site and would need a separately proven context access. This gap contributes to `G19` failure.

## Real listener contract (design only)

No real socket is started. A future listener implementation must satisfy this contract before response serialization:

1. Create an IPv4 TCP socket on the interface/address actually reachable by the CarPlay phone; do not guess wildcard vs interface binding. Bind port `0` and retrieve the assigned port with `getsockname`; publish only that value. Reject invalid ports and never reuse a stale generation's port reservation.
2. Set close-on-exec before handing ownership to another component; set nonblocking mode only if the accept/read state machine uses poll/select with bounded timeouts. Otherwise use a dedicated project-owned worker and cancellation path. No listener implementation may block the Honda serializer thread.
3. Complete bind and listen before serialization so a phone that connects immediately after response receipt cannot race listener startup. Backlog, address-family behavior, interface selection, socket options, process/thread model and phone connection timing still require exact-target verification.
4. Transfer the descriptor to exactly one Type111 generation owner. The owner closes it once on serializer failure, timeout/lease expiry, socket/session teardown, new transport generation, or explicit disable. Stale cleanup carries the exact generation key and cannot close a replacement listener. Accepted sockets and workers are also generation-owned and joined/cancelled before state release.
5. On socket/bind/listen/port lookup/worker failure, do not advertise Type111; run the stock serializer once with its untouched response. If the phone never connects, expire the exact B generation and close all owned descriptors. If the phone connects immediately, accept is safe because listen precedes serialization.
6. Log only coarse phase/error codes, generation-local counters, and port allocation success/failure; do not log raw UUIDs, stream IDs, keys, payloads, or peer addresses.

Android 4.2.2 provides the ordinary Linux/Bionic socket API family, but the repository has not verified the exact compiler/runtime/threading/linking surface of the eventual in-process adapter, descriptor ownership across its actual process path, or phone-reachable interface. Thus this is a concrete engineering contract but not an implementable, validated Honda runtime contract; `G11` and `G12` do not pass for a first live experiment.

## Security-mode decision gate

Honda Type111 stays `HONDA_UNKNOWN`. The future receiver may classify only after evidence at the accepted Type111 boundary identifies framing, authentication, key derivation inputs, and a known-good integrity check against captured/controlled Type111 bytes:

- `LEGACY_AES_CTR_SCREEN`: only if exact Type111 evidence proves the Honda legacy ScreenStream header/KDF and continuous AES-CTR semantics.
- `MODERN_CHACHA_SCREEN`: only if exact Type111 evidence proves the corresponding authenticated modern framing, key schedule, nonce/counter and tag validation.
- `CLEAR_OR_UNKNOWN`: no established security branch; do not parse/decrypt speculatively.
- `UNSUPPORTED`: contradictory, malformed, unauthenticated, or unsupported framing.

All but an evidence-backed supported branch fail closed: close the accepted socket, retire only the exact B generation and keep Type110 untouched. Do not try Honda Type110 AES by analogy or PlayPort ChaCha by analogy. `G13` passes as a policy boundary; `G14` passes as an explicit future rule, but no live security mode is established.

## Media receiver boundary and Display 1

Future boundary: accept Type111 socket → identify framing/security → create generation-owned receiver → parse VideoConfig → expose encoded access units → decoder. Any failure tears down only B-owned resources. 43Q ownership rules already model separation from Type110; no actual Honda receiver path has been established.

Honda evidence supports Display 1 / `ExternalDisplayOutService` and approximately 800×480 Android Display 1. The physical visible aperture remains unproven. Keep media transport resolution, Android Surface bounds, physical/logical Display 1 size, visible aperture, CarPlay ViewArea and SafeArea as separate values. Do not revive 584×215 or 584×191 as Honda-confirmed geometry. Geometry is **not required before negotiation-only testing**; it is required before any first decoded-frame presentation contract and must be measured before polished user-visible rendering. No Display 1 change is needed for negotiation proof.

## Rollback and safety

- Keep runtime attachment mechanically disabled; current state emits no patch bytes and has no startup integration.
- A future enable operation must verify whole ELF SHA and callsite/context/prologue fingerprints before any action. Disable/rollback must verify the current callsite contains the exact installed replacement before restoring original bytes `fe f7 d1 ff`; any mismatch aborts without writing. Verify restored bytes and original hash/fingerprint after rollback.
- Prefer a one-shot, nonpersistent offline or RAM-only enablement mechanism with an independent timeout/disable path. No persistence design is currently demonstrated; init/startup edits remain out of scope.
- Adapter crash or listener failure must leave the original response unmodified and take the stock serializer path. Serializer failure retires B and returns Honda's original result/status. A phone that never connects expires B. The actual machine-code crash containment behavior remains unproven and blocks GO.
- Any future vehicle experiment remains parked, stationary, and non-driving; preserve stock safety-critical cluster information, make no CAN writes, and change no vehicle-control systems. First live test is negotiation observation only, with stock Type110/audio checks and no rendering attempt.

## Required gate matrix

| Gate | Decision | Evidence / blocker |
|---|---|---|
| G1 exact Honda binary identity | PASS | Preserved artifact and independently matched SHA/ELF identity. |
| G2 exact callsite bytes | PASS | Exact `fe f7 d1 ff` plus context fingerprint. |
| G3 BL target | PASS | Decodes to `0x289f60`. |
| G4 continuation | PASS | `0x28afbe`, original Thumb LR `0x28afbf`. |
| G5 trampoline ABI model passes | **FAIL** | Synthetic only; no executable adapter/ARM emulator proof or crash containment. |
| G6 stock/no-Type111 path | PASS, offline only | 43R unchanged stock response path. |
| G7 serializer exactly once | PASS, offline model only | 43R and synthetic wrapper tests. |
| G8 43R transaction integrates offline | PASS | Type111 response, listener reservation, serializer predicate, rollback modeled. |
| G9 malformed input fails closed | PASS, offline | Sanitized errors and unchanged-stock fallback. |
| G10 Type110 remains untouched | PASS, offline | Independent ownership/response invariants. |
| G11 listener runtime contract concrete | **FAIL** | Interface binding/process ownership/API compatibility remain target-specific and unverified. |
| G12 listener rollback concrete | **FAIL** | Exact generation cleanup modeled; no real FD/worker ownership and rollback behavior verified. |
| G13 Type111 crypto explicitly unknown | PASS | Preserved as `HONDA_UNKNOWN`. |
| G14 unknown security fails closed | PASS, policy only | Defined close-and-retire rule; no live branch identification. |
| G15 generation ownership preserved | PASS, offline | 43Q-B/43R exact-generation ownership and synthetic control split. |
| G16 stale-generation cleanup preserved | PASS, offline | Existing versioned lease and exact-key teardown tests. |
| G17 sanitized logging | PASS, offline model | Existing allowlisted diagnostics/redaction tests; no raw peer IDs in new model. |
| G18 rollback/disable strategy defined | PASS, design | Exact-byte/hash-gated restoration; no persistence implemented. |
| G19 no required Honda runtime prerequisite guessed | **FAIL** | Request/session context acquisition at serializer seam, reentrant callout safety, listener reachability, and crash containment remain unproven. |
| G20 first live experiment negotiation-only | PASS, plan | Future test can stop at serializer local success and phone connection attempt; no decode/render prerequisite. |

Because required gates G5, G11, G12 and G19 fail, the required result is **`NO_GO`**. Geometry, final codec/decode/presentation, provider recovery, and long-duration stability are nonblocking for negotiation-only testing and are not used to manufacture this decision.

## Offline validation

- Focused readiness, exact-binary planner, trampoline, 43R SETUP, 43Q-A/B lifecycle/crypto and provenance set: **69 passed**.
- Configured offline suite: **352 passed, 4 expected skips**.
- Self-locator smoke: **3 passed**.
- Configured simulator checks: **PASS** (contract adapter, dual-screen state, guidance expiry, Type111 failure twin).
- `git diff --check`: **PASS**.
- Documentation local-link check: **PASS for links in this report and updated index entries**.
- `tools/run_tests.sh` without a `PYTHON` override could not find system pytest; rerun with `PYTHON=.venv/bin/python` passed all configured checks.
- Hosted Offline CI: **PASS** on implementation commit `19102b0256c2fa2e04a84c15201c26e38112a01f`, [run 36967581461](https://github.com/bmreyes25/ClarityLink/actions/runs/36967581461).

## Smallest follow-up milestone

**43S1 — executable offline trampoline and real-listener contract proof.** Do not touch Honda. Build an ARM32/API-17 compatible synthetic adapter artifact (no Honda binary modification), exercise it in an ARM emulator, and validate registers/stack/statusOut/exactly-once stock delegate/fault behavior. Separately implement and test an OS-socket listener in a host harness with explicit interface policy, FD/worker ownership, early-connect race, timeout, and exact-generation rollback. Then re-audit whether a bounded request/session context is available at the Honda callsite without unsafe lookup or reentrancy. Only after every failed gate is closed should a new review reconsider a parked negotiation-only experiment.

## Completion record

Starting HEAD `5abb244fdeb7bf652cb2982991cb04c4fc4a0045`; final implementation HEAD `19102b0256c2fa2e04a84c15201c26e38112a01f`. Offline review committed and pushed; hosted Offline CI passed (run 36967581461). Honda runtime remains disabled; decision `NO_GO`.
