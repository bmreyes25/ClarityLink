# Honda session delegate and finalizer lifecycle — Step 43I

**Scope:** offline static analysis only. Artifact: `extracted/system/system/bin/jmcs`, SHA-256 `cbc7ba881648fb8ffdfcc4c1100a028345c37134a2ae3b9dff7d76572851c232`. Address values below are ELF virtual addresses in the verified 32-bit ARM/Thumb image. Evidence is `HONDA_CONFIRMED` unless marked otherwise.

## Runtime class and finalizer

`kAirPlayReceiverSessionClass` at VA `0x3427d4` is an 11-word class record. Its name pointer at `+0x04` resolves to the `AirPlayReceiverSession` string at `0x333419`; its finalizer slot at `+0x10` contains Thumb pointer `0x284d25`, normalized to `_Finalize` at `0x284d24`. `AirPlayReceiverSessionGetTypeID` (`0x284e28`) registers that class through `_CFRuntimeRegisterClass`; `AirPlayReceiverSessionCreate` (`0x284e58`) creates a `0x1420` byte runtime instance with `_CFRuntimeCreateInstance`. **`HONDA_SESSION_CFRUNTIME_CLASS: PROVEN`.**

At `0x284d30–0x284d36`, `_Finalize` loads the callback at session offset `+0x20`, checks it, loads context from `+0x14`, and calls it with the session in `r0` and context in `r1`. Then it calls `AirPlayReceiverSessionPlatformFinalize` (`0x28cd60`), `_ScreenTearDown` (`0x284628`), `_TearDownStream.isra.1` twice (`0x284bd8`), `_ControlTearDown` (`0x284c98`), `_TimingFinalize` (`0x2846c4`), `AirTunesClock_Finalize` (`0x28980c`), cancels/releases a dispatch source, finalizes AES-CBC frame state, deletes the session screen object, and releases/clears retained server/dispatch references. Thus the application callback occurs before the remaining finalizer cleanup. The recovered sequence is not a proof of crypto zeroization beyond the observed AES finalization call.

`AirPlayReceiverSessionPlatformFinalize` stops HID, clears a platform flag, calls `_TearDownStreams(session, 0)`, frees the platform context, and clears `session+0x10`.

## Delegate installation and callback slots

`AirPlayReceiverSessionSetDelegate` at `0x285040` copies exactly 11 32-bit words (44 bytes) from its second argument to session offset `+0x14`. This proves whole-structure replacement in this binary; it does not establish source-level field names for all slots.

`_AirPlayThread` at `0xaebd8` constructs a 7-word server delegate and calls `AirPlayReceiverServerSetDelegate` at `0xaec a2` (instruction address `0xaeca2`; symbol entry `0x28392c`). The server setter copies seven words (28 bytes) to server offset `+0x10`. The callback value in server delegate slot `+0x14` resolves to `_AirPlayHandleSessionCreated` (`0xaf04c`); slot `+0x18` resolves to `_AirPlayHandleSessionFailed` (`0xa6144`). In `AirPlayReceiverSessionCreate` (`0x284e58`), the callback at server offset `+0x24` is invoked with server/context, newly created session, and server context. This aligns the installed callback slot with the actual session creation call. **`HONDA_SESSION_CREATED_CALLBACK: PROVEN`.**

`_AirPlayHandleSessionCreated` (`0xaf04c`) allocates a 16-byte application context and lays out the 44-byte session delegate on its stack before calling `AirPlayReceiverSessionSetDelegate` at `0xaf252`. The value at delegate offset `+0x0c` is Thumb pointer `0xae655`, `_AirPlayHandleSessionFinalized` (`0xae654`). The context pointer is the delegate's first word and is passed by `_Finalize` as argument 2. Other non-null callback pointers in the copied table resolve to Honda application handlers for session copy-property, modes-changed, request-UI, duck-audio, and unduck-audio; fields not populated in this creation path are zero. The recovered behavior is enough to prove the finalizer slot and existing callback; it is not a claim that the Honda layout is source-identical to a particular external version.

| Delegate offset | Honda value written by session-created callback | Resolved target/role | Evidence |
|---:|---|---|---|
| `+0x00` | allocated app context | context passed to delegate callbacks | `HONDA_CONFIRMED` |
| `+0x04`, `+0x08` | null | no callback installed here | `HONDA_CONFIRMED` |
| `+0x0c` | `0xae655` | `_AirPlayHandleSessionFinalized` | `HONDA_CONFIRMED` |
| `+0x10` | session control handler | `_AirPlayHandleSessionControl` | `HONDA_CONFIRMED` |
| `+0x14` | `0xae4e5` | `_AirPlayHandleSessionCopyProperty` | `HONDA_CONFIRMED` |
| `+0x18` | null | no callback installed here | `HONDA_CONFIRMED` |
| `+0x1c` | `0xa7e89` | `_AirPlayHandleModesChanged` | `HONDA_CONFIRMED` |
| `+0x20` | `0xa6661` | `_AirPlayHandleRequestUI` | `HONDA_CONFIRMED` |
| `+0x24` | `0xa6469` | `_AirPlayHandleSessionDuckAudio` | `HONDA_CONFIRMED` |
| `+0x28` | `0xa6291` | `_AirPlayHandleSessionUnduckAudio` | `HONDA_CONFIRMED` |

The delegate structure is copied, not merged. The existing callback is non-null. No Honda behavior in this step modifies, replaces, or chains it.

### R11B structural comparison (external fingerprint only)

| Offset | Honda recovered behavior | R11B field | Match class |
|---:|---|---|---|
| +0x00 | application context | context | EXACT_STRUCTURAL_MATCH |
| +0x04 | null | context2 | EXACT_STRUCTURAL_MATCH |
| +0x08 | null | initialize_f | EXACT_STRUCTURAL_MATCH |
| +0x0c | session-finalized callback | finalize_f | EXACT_STRUCTURAL_MATCH |
| +0x10 | session-control callback | control_f | EXACT_STRUCTURAL_MATCH |
| +0x14 | copy-property callback | copyProperty_f | EXACT_STRUCTURAL_MATCH |
| +0x18 | null | setProperty_f | EXACT_STRUCTURAL_MATCH |
| +0x1c | modes-changed callback | modesChanged_f | EXACT_STRUCTURAL_MATCH |
| +0x20 | request-UI callback | requestUI_f | EXACT_STRUCTURAL_MATCH |
| +0x24 | duck-audio callback | duckAudio_f | EXACT_STRUCTURAL_MATCH |
| +0x28 | unduck-audio callback | unduckAudio_f | EXACT_STRUCTURAL_MATCH |

All 11 slots including null/populated pattern align; `HONDA_R11B_DELEGATE_FINGERPRINT: STRONG`. R11B's source-level names remain external labels, not newly asserted Honda facts.

## Request-aware stream teardown

`AirPlayReceiverSessionTearDown` (`0x2852ec`) calls `AirPlayReceiverSessionPlatformControl` (`0x28cd88`) at `0x285364`, before its later teardown work. It passes the session, flag `1`, the CFString object whose backing text is `tearDownStreams`, null qualifier, the original request (`r5`) as the first stack argument, and null output pointer. The literal object begins at `0x3373d7`; its backing text begins at `0x3373e7`.

`AirPlayReceiverSessionPlatformControl` compares the command and reads typed stream dictionaries from the request array. The `tearDownStreams` branch at `0x28cfe0` extracts each stream type; 100/101 select separate platform state slots and 110 takes the platform update path. Unknown types log and continue. This branch never loads/calls the delegate control slot at `session+0x24`; that indirect callback is only on the unmatched-command path at `0x28d2c2–0x28d2d6`. Consequently `TEARDOWNSTREAMS_TO_DELEGATE_CONTROL=NO`, and `TYPE111_CURRENT_PLATFORMCONTROL_RESULT=IGNORED` (unknown type, no application callback). The detail and synthetic lifecycle contract are in [Step 43J](../../step-reports/43j-platform-lifecycle-seam.md).

The finalizer has a single direct call to `AirPlayReceiverSessionPlatformFinalize` per CF finalizer invocation. That helper skips safely with no platform pointer; otherwise it invokes `_TearDownStreams(session, NULL)`, frees the platform state, and clears `session+0x10`. Stream-level request handling and final object destruction are separate Honda paths. This is a full-session cleanup safety signal independent of HTTP or earlier teardown.

## Three-layer lifecycle matrix

| Event | HTTP close | `AirPlayReceiverSessionTearDown` | `tearDownStreams` PlatformControl | delegate finalizer | session object release |
|---|---|---|---|---|---|
| Setup failure | Depends on calling path; see Step 43H | Unknown for all Setup failures | Unknown | Only if object reaches finalization | Unknown |
| Type110-specific request | Not established | Request-aware path exists; exact caller-dependent effect | Type 110 recognized and distinguished in this path | No, unless object later finalizes | Unknown |
| Connection failure | HTTP connection stop/close proven in Step 43H | Conditional on non-null session at connection finalizer | Yes when TearDown is called | Later, when the session object reaches CF finalization | Conditional/deferred |
| Peer disconnect | HTTP terminal read path in Step 43H | Conditional as above | Conditional | Conditional | Conditional/deferred |
| Idle/session death | `sessionDied` strings exist; semantic path not established | Unknown | Unknown | Unknown | Unknown |
| Final reference release | Not required | Not necessarily called here | Finalizer's PlatformFinalize does `_TearDownStreams(session,0)` | `_AirPlayHandleSessionFinalized` called by `_Finalize` | CF runtime finalization path |

## Project-child lifecycle assessment

The Honda binary proves `_AirPlayHandleSessionFinalized(session, context)` is installed and called before platform/stream teardown. It remains Honda-owned. The project design does not replace or extend this delegate; its lifecycle model uses the platform request path and finalization cleanup semantics, with safe interception still unproven. `AirPlayReceiverSessionSetDelegate` overwrites the whole table, so a project-only delegate would erase current callbacks and is explicitly unsafe.

The platform layer supplies both lifecycle semantics: request-aware teardown reaches the platform parser (but not the app delegate), and PlatformFinalize is the unconditional session-object cleanup path. The external ClarityLink registry/idempotent-child contract is ready for offline prototype. This proves lifecycle semantics, not safe interposition or extension. Project cleanup attachment and post-Setup child creation still need static integration proof.

## Reproducibility

Address mapping used the preserved `tools/elf_va_map.py` against PT_LOAD segments; Thumb function pointers had bit 0 cleared for disassembly, while stored callback values are reported with the Thumb bit where relevant. Disassembly used Xcode's `llvm-objdump`; data words and literals were read by VA from the hash-matched ELF. No Honda code was executed.
