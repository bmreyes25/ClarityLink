# Honda hook fingerprints — Step 40

## Exact local build

| Invariant | Value | Status |
|---|---|---|
| ELF SHA-256 | cbc7ba881648fb8ffdfcc4c1100a028345c37134a2ae3b9dff7d76572851c232 | CONFIRMED |
| ELF type / class / endian / machine | ET_DYN / ELF32 / little / EM_ARM (40) | CONFIRMED |
| File size | 13,406,720 bytes | CONFIRMED |
| .text VA / file offset / size | 0x13100 / 0x13100 / 0x2a0b82 | CONFIRMED |
| .text SHA-256 | ca4abfd2f2c1f5f7fe88b4b0bde9e920d22b454f2a699b7de1f4984c901278eb | CONFIRMED |
| GNU build-id | absent; .note.android.ident identifies Android API 17 | CONFIRMED |

All fingerprints below are raw bytes from that ELF. Disassembly is Thumb-2; static symbol VAs are even.

## Selected call-site candidates

| Target | VA | Raw instruction bytes | Disassembly | Patch span / hazard |
|---|---:|---|---|---|
| AirPlayCopyServerInfo call in _requestProcessInfo | 0x28a158 | f8 f7 bc fd | bl 0x282cd4 | One 32-bit Thumb BL (4 bytes). PC-relative branch; a replacement must call original directly and return to 0x28a15c. No branch veneer/shim or runtime range validated. Not a prologue patch. |
| AirPlayReceiverSessionSetup call in _connectionHandleMessage | 0x28af72 | fa f7 b5 fa | bl 0x2854e0 | One 32-bit Thumb BL (4 bytes). Replacement must preserve call/return and stock result semantics. No shim or runtime range validated. Not a prologue patch. |

Both sites are halfword-aligned and outside an IT block in the surrounding disassembly. Their BL displacement is PC-relative but is not copied into a trampoline in the proposed call-site design. A nearby executable veneer, branch-range check, exact instruction encoder, cache maintenance, page protections, synchronization, and uninstall behavior remain unimplemented.

## Function entry bytes inspected

| Function | VA | Raw initial bytes | Relevant disassembly / hazard |
|---|---:|---|---|
| AirPlayReceiverSessionSetup | 0x2854e0 | 2d e9 f0 4f 00 26 9e 4d c1 b0 | push.w {r4-r11,lr}; movs r6,#0; ldr r5,[pc,#...]; literal load starts at +6. |
| AirPlayCopyServerInfo | 0x282cd4 | 2d e9 f0 4f ad f5 86 5d df f8 bc 67 | push.w; sub.w sp; ldr.w r6,[pc,#...]; PC-relative literal early. |
| _connectionHandleMessage | 0x28a30c | df f8 8c 24 2d e9 f0 4f 04 46 df f8 88 04 | Starts with PC-relative literal load before stack frame setup. |
| _requestProcessInfo | 0x28a018 | 2d e9 f0 4f 06 46 d0 f8 08 a0 91 b0 90 48 | Push/move then PC-relative load and literal load in initial window. |
| _requestSendPlistResponse | 0x289f60 | f7 b5 1e 46 d0 f8 c8 50 14 46 05 f5 00 50 | Push frame; broad generic response serializer. |
| AirPlayReceiverSessionScreen_Setup | 0x287d5c | 0a 4b 13 b5 7b 44 | Literal load, push, then add r3,pc; PC-relative. |
| AirPlayReceiverSessionScreen_ProcessFrames | 0x287d8c | 2d e9 f0 4f 2d ed 02 8b 93 46 86 4d | Push core/VFP registers and frame; media hook not selected. |
| AirPlayReceiverSessionScreen_StartSession | 0x2883a8 | 25 a3 d3 e9 00 23 2d e9 f0 41 | Begins adr + ldrd using PC; unsuitable for naive entry-copy trampoline. |
| AirPlayReceiverSessionStart | 0x286398 | 2d e9 f0 4f cb b0 f8 4c 05 46 88 46 | Early PC-relative literal load. |
| AirPlayReceiverSessionTearDown | 0x2852ec | 2d e9 f0 4f 04 46 6d 48 9a 46 8d b0 | Early PC-relative literal load. |
| AirPlayReceiverSessionScreen_CopyDisplaysInfo | 0x287ae0 | 00 20 86 4a 86 4b 2d e9 f0 47 | Literal loads before frame setup. |

The exact bytes are machine fingerprints only. Function-entry relocation is **NOT READY**. This milestone does not encode executable branch instructions or claim any patch span as live-safe. Fingerprint extraction/comparison is implemented in src/claritylink-honda/targets.py and hook_gate.py.

## Relocation hazard matrix

“Minimum patch length” below is the minimum instruction span of a proposed strategy only where the strategy is a single call-site BL replacement. No function-entry patch length is approved; the encoder/entry patch architecture is not implemented.

| Candidate | Minimum patch length | PC-relative / literal pool | Branch / IT in initial span | Frame setup / relocation note |
|---|---:|---|---|---|
| Info BL call-site 0x28a158 | 4 bytes (one Thumb BL) | Relative BL target; no literal copied | BL present; not in IT | No prologue/frame; wrapper must call original AirPlayCopyServerInfo and return its result |
| Setup BL call-site 0x28af72 | 4 bytes (one Thumb BL) | Relative BL target; no literal copied | BL present; not in IT | No prologue/frame; wrapper must call stock Setup once and preserve responseOut/status |
| AirPlayReceiverSessionSetup entry | Not approved | LDR literal at +6, pool target around +0x280 | no branch in first 10 bytes | Push then stack allocation. Inline relocation requires literal-load handling and correct PC semantics |
| AirPlayCopyServerInfo entry | Not approved | LDR.W literal at +8 and further early PC-relative references | no branch in first 12 bytes | Large stack frame setup; no entry trampoline |
| _connectionHandleMessage entry | Not approved | First instruction is LDR.W literal | no branch in initial span | Literal load occurs before push/frame setup; unsuitable for naive overwrite |
| _requestProcessInfo entry | Not approved | PC-relative LDR.W and literal LDR within initial 14 bytes | no branch in initial span | Function owns broad HTTP dispatch work; not selected |
| _requestSendPlistResponse entry | Not approved | No PC-relative operand in bytes shown through +0xd; later instructions not assessed here | no branch in initial 14 bytes | Push includes r0-r2; generic response path, not selected |
| Screen_Setup entry | Not approved | Starts LDR literal then ADD PC | no branch in first 6 bytes | Literal/PC-relative dependency before function body |
| ProcessFrames entry | Not approved | Literal load appears at +0x0a | no branch/IT in first 10 bytes shown | Push and VFP push; media hook excluded |
| Screen_StartSession entry | Not approved | ADR at +0; LDRD using computed PC value at +2 | no branch in first 10 bytes | PC-relative setup precedes stack frame; no trampoline |
| SessionStart entry | Not approved | LDR literal at +4 | no branch in first 12 bytes | Push and stack allocation; lifecycle ABI still needs safe wrapper analysis |
| SessionTearDown entry | Not approved | LDR literal at +6 | no branch in first 12 bytes | Push then stack allocation; lifecycle ABI still needs safe wrapper analysis |
| CopyDisplaysInfo entry | Not approved | LDR literal at +2 and +4 | no branch in first 10 bytes | Literal loads precede push; not selected |

Selected call-site fingerprints are recoverable, but no nearby veneer address, Thumb BL encoding to a shim, original-call bridge, executable mapping permissions/cache workflow, or live rollback sequence is proven. Therefore the prologue fingerprints are suitable for host identity checking only, not approval to patch.
