# Step 43S1 — executable trampoline and real-listener contract proof

**Decision: `43S1_NO_GO`.** This offline milestone produced and executed a standalone ARMv7 Thumb shim and a host-socket listener with real FD/worker lifecycle tests. It closes much of the implementation-contract gap, but the compiled project transaction helpers remain emulator callbacks rather than a native, executable 43R transaction implementation. Same-process nested/reentrant transaction behavior and some request/session pointer validity assumptions therefore remain unproven. Do not start 43S2 vehicle work; keep Honda runtime/deployment disabled.

## Starting state and boundary

- Starting HEAD: `c3408f08373c61514e58c25cbc7266b374bb21a6` (43S `NO_GO`).
- Scope: offline preserved-binary inspection, standalone shim, Unicorn execution, host-only sockets, tests, documentation and ECC manual review.
- Honda/ADB/runtime access: none. No jmcs patch, patch payload, install artifact, startup persistence or LD_PRELOAD was produced. The preserved ELF was read-only evidence.

## External research update

Recent public work reports vehicle demonstrations of real Type111/Stream-111 native CarPlay secondary navigation on VW Group MHI2 and Audi MHI2Q platforms, with the main CarPlay display remaining available. The MHI2 project describes Apple Maps, Google Maps and Waze through the secondary video path and identifies SafeArea/ViewArea tuning, UI ownership and presentation refresh as ongoing work. MHI2Q reports a vehicle-validated AltScreen path on its stated vehicle/firmware scope. These are `EXTERNAL_PHYSICAL_VALIDATION` for those platforms and `EXTERNAL_PRIOR_ART` for ClarityLink. The MHI2 lifecycle observations support separating UI/ViewArea changes from transport generation; they do not establish Honda support. [MHI2 AltScreen project](https://github.com/harman-f/mhi2_altscreen_carplay), [MHI2Q AltScreen project](https://github.com/yuedizhibo/MHI2Q-CarPlay-AltScreen/blob/main/README_EN.md).

Current public iOS reverse-engineering notes continue to describe `altScreen`, `viewAreas`, `altScreenURLs` and ScreenAlt concepts (`EXTERNAL_PRIOR_ART`); 43P remains the project’s `CURRENT_IOS_LAB_CONFIRMED` source for its test phone. [CarPlay capability notes](https://github.com/lvalen91/carlink_linux/blob/main/docs/CARPLAY_CAPABILITIES.md). None of this changes Honda evidence classification.

## Reference artifact and callsite audit

Revalidated against preserved firmware before implementation:

| Fact | Result | Classification |
|---|---|---|
| jmcs SHA-256 | `cbc7ba881648fb8ffdfcc4c1100a028345c37134a2ae3b9dff7d76572851c232` | `HONDA_CONFIRMED` |
| ELF / ABI | ELF32, ARM, little-endian, EABI5; ARM32 Thumb caller | `HONDA_CONFIRMED` |
| Callsite | `0x28afba`, bytes `fe f7 d1 ff` | `HONDA_CONFIRMED` |
| Decoded direct Thumb BL | `_requestSendPlistResponse` at `0x289f60` | `HONDA_CONFIRMED` |
| Continuation / LR | `0x28afbe` / Thumb return state `0x28afbf` | `HONDA_CONFIRMED` |
| Caller | `_connectionHandleMessage` at `0x28a30c`; frame delta `0x2d8`; SP 8-byte aligned at seam | `HONDA_CONFIRMED` |
| Context offsets | request `SP+0x1c`; statusOut `SP+0x50`; response `SP+0x54`; session `*(r10+0xf4)` | `HONDA_CONFIRMED` |

An independent Thumb BL immediate decode and the existing self-locator/planner agree with the target. The new artifact test rejects a modified callsite byte sequence. The standalone shim validator checks ARM EABI5, executable non-writable text, a 512-byte bound, Thumb entry, local call relocation shape and required symbols. It is informational and emits only an in-memory emulator image; it cannot generate jmcs patch bytes.

## Executable shim and ABI result

`thumb_setup_shim.S` compiles with the available Apple Clang targeting `armv7-none-eabi`; Unicorn 2.1.4 executes its actual Thumb instructions. The shim snapshots incoming SP to r12 before allocating its frame, reads caller offsets through that saved value, captures the session pointer only when r10 is non-null, stores original r0-r3, checks the known statusOut address and serializer success predicate, invokes the synthetic serializer once, returns the exact serializer r0, restores SP and r4-r11, and returns through saved LR.

Evidence: `LAB_EXECUTABLE_CONFIRMED` for the shim instructions and ABI harness. The serializer and project prepare/finish boundaries are controlled synthetic callbacks; this is not Honda execution. ABI constraints tested include 8-byte SP alignment at call boundaries, callee-saved register restoration, serializer caller-saved clobbering, exact-once invocation, result propagation, continuation, successful/failed prepare, malformed/no-Type111 fallback, non-success serializer result and nonzero statusOut. Null request/response are passed through without commit. Null r10 is bounded. An invalid non-null pointer or corrupt stack would fault; the shim does not claim to recover from native memory faults.

G5 is **PASS for the shim contract under the emulator**, with the explicit limit that actual project helper implementations are not machine-code linked into the artifact. Request/context acquisition is proven only for the supplied mapped synthetic caller frame; Honda runtime pointer validity and reentrant transaction safety are not thereby established.

## Three-plane readiness

| Plane | Offline result | Honda unknowns |
|---|---|---|
| Negotiation | 43R SETUP transaction composed with a real host listener; bind/listen/readiness precedes advertisement; stock serializer called once; listener reservation is committed only on the local success predicate. Host tests show unchanged Type110-only fallback and unchanged stock response when preparation fails. | Honda Type111 acceptance, listener ABI/reachability and response runtime behavior remain `HONDA_UNKNOWN`. |
| Media | No media receiver or decryptor was added. Unknown security mode remains fail-closed: close accepted socket, retire that exact generation, leave Type110 untouched. | Honda Type111 security, framing, ScreenStream, VideoConfig and decode remain `HONDA_UNKNOWN`. No AES/ChaCha mode selected. |
| Control/presentation | Kept separate from transport generation. No UI-control implementation added. 43P observed suggestUI; showUI/stopUI/forceKeyFrame remain unconfirmed on the current phone. | Honda control behavior, UUID policy, ViewArea/SafeArea and visible aperture remain `HONDA_UNKNOWN`. |

Negotiation proof, TCP acceptance, security/framing identification, frame parsing, decode, Display 1 test output and navigation presentation remain separate future stages. Display 1 is not changed by this milestone.

## Real listener contract

The host reference implementation uses synchronous `socket` → non-inheritable/timeout options → `bind(port=0)` → `getsockname` → `listen` → joinable worker readiness, before the response is advertised. A client can connect immediately across the simulated serializer boundary. The worker performs bounded-timeout accept off the caller thread, owns the accepted socket until generation handoff/cleanup, and is cancellable and joined. Interface modes exercised on host: `LOOPBACK_TEST`, `SPECIFIC_ADDRESS`, `WILDCARD_TEST_ONLY`; production `HONDA_INTERFACE_POLICY` remains unresolved.

Generation ledger is keyed by exact generation identity and owns listener socket, accepted socket, worker and cancellation state. Tests exercise stale B42 cleanup after B43 replacement, socket/setup/worker/accept failures, serializer and commit failures, timeout, client drop, parent teardown, explicit disable and concurrent independent generations. A process FD-count loop and join assertions supplement internal ownership counters. Evidence is `LAB_HOST_RUNTIME_CONFIRMED`, not Honda runtime. `jmcs` preserved imports provide static evidence for ordinary socket and pthread APIs (`HONDA_STATIC_COMPATIBILITY`); Android/Bionic behavior, interface choice and actual phone reachability are not proven.

G11: **PARTIAL** — real listener machinery works on host; Honda interface selection/reachability remains an isolated observation prerequisite. G12: **PASS for host reference listener rollback/FD ownership**; this does not prove target Bionic or Honda lifecycle behavior.

## Security, rollback and safety

Honda Type111 security stays `HONDA_UNKNOWN`. Unknown framing is unsupported and must close the exact generation’s accepted FD, retire only that generation, and preserve Type110. No parser fallback is allowed.

Future disable design remains nonpersistent and exact-byte gated: validate the known binary hash and original callsite bytes before any hypothetical restoration; reject any mismatch. A future test should use the smallest reversible mechanism, no startup persistence, and return to stock by disabling/removing the experimental attachment and restarting the relevant process only under a separately reviewed plan. This milestone creates no persistence or installation payload. Ordinary project failures must be returned before Honda stock response mutation; arbitrary invalid instruction, stack corruption or native memory faults cannot be safely contained in-process.

Any future vehicle test remains parked/stationary, negotiation-only, with stock cluster safety information preserved, no CAN writes and no vehicle-control changes. This report authorizes no vehicle access.

## Gate reassessment

| Gate | Result | Evidence / limit |
|---|---|---|
| G5 executable trampoline ABI | PASS (bounded) | Compiled Thumb artifact executed by Unicorn; actual helper transaction bodies are synthetic callbacks. |
| G11 real listener contract | PARTIAL | Real OS sockets, listener readiness and immediate-connect race proven on host; Honda interface/reachability unresolved. |
| G12 rollback / FD / worker | PASS (host reference) | Failure injection, exact-generation cleanup, FD accounting and worker joins; target runtime remains unproven. |
| G19 context, reentrancy, reachability, failure containment | PARTIAL / FAIL gate | Context offset acquisition executes with a valid synthetic frame; nested and independent concurrent shim invocations pass in isolated Unicorn instances. Native 43R transaction-helper/reentrant behavior is not proven. Honda pointer validity, Bionic behavior and in-process native-fault containment are not claimed. |

**Required outcome: `43S1_NO_GO`.** The offline evidence does not justify a new negotiation-only readiness GO review while G19 remains open. This is an implementation-contract blocker, not a reason to guess Honda behavior. Honda Type111 crypto/media/rendering/geometry are intentionally untouched and are not the reason for this result.

## ECC review and verification

No dedicated ECC reviewer tool was available. I applied ECC security, ABI, memory-safety, concurrency, FD ownership, failure-injection, evidence-classification and test-quality checklists manually. The review found no justified basis to claim recovery from arbitrary native faults, no project-global transaction state in the shim, and a real listener self-close/join edge that was corrected and retested. Residual blocker: nested/reentrant native transaction execution is not covered by the compiled harness.

Verification: focused trampoline/listener/43R/fingerprint tests **51 passed**; configured offline suite **384 passed, 3 skipped**; self-locator **3 passed**; simulator checks **PASS**; `git diff --check` **PASS**; touched-document relative Markdown links **PASS**. ARM shim build and `llvm-objdump -d -r` validation **PASS**; Unicorn **2.1.4**.

Focused, full-suite and simulator results are recorded in the completion record after final verification. Relevant designs: [executable trampoline ABI](../research/carplay/executable-trampoline-abi.md), [listener runtime contract](../research/carplay/type111-listener-runtime-contract.md), and [listener ownership](../research/carplay/type111-listener-ownership.md).

## Smallest follow-up

**43S2 — native helper/reentrancy proof and repeat readiness review.** Compile the bounded 43R prepare/commit/rollback transaction implementation into the emulator artifact (no helper boundary callbacks), exercise nested invocation and replacement/teardown races against shared synchronized session state, and resolve whether the request/session pointers have a bounded checked acquisition contract or remain a runtime-only observation prerequisite. Then reassess G5/G11/G12/G19 in a fresh readiness review. No vehicle work until that independent review returns GO.
