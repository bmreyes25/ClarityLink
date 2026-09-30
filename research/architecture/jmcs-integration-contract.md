# Offline jmcs integration contract

Future boundary only: no hook, patch, preload, or load seam is implemented or approved. Archived Honda evidence places CarPlay Setup/session and Type110 state in jmcs.

## Ownership and call order

Phone Setup -> stock jmcs Setup -> if failure, return stock failure and allocate no ClarityLink resources -> if success, retain immutable stock response -> prepare isolated Type111 candidate -> on success append candidate entry to a copy -> on any project failure close only candidate resources and return stock response -> Honda serializes/sends through its existing path.

The phone-facing /info response is a separate candidate extension point: a stock display array exists but its builder emits one descriptor. Append a candidate descriptor only after the exact capability generation and phone behavior are justified.

## Inputs

| Input | Evidence/source | Type111 requirement | In jmcs | Outside jmcs | Safe model |
|---|---|---:|---:|---:|---:|
| Authenticated session handle | Honda session owner confirmed; extension ABI unknown | Yes | Likely; exact handle unknown | No transfer API found | Opaque synthetic token |
| Original Setup request and streams | Honda-confirmed | Yes | Yes | Not via reviewed Binder | Synthetic plist/dict |
| Stock Setup status/response | Honda-confirmed | Yes | Yes | Not via reviewed Binder | Yes |
| /info displays collection | Honda array confirmed, stock adds one | Conditional | Yes | No mutation API found | Evidence profile |
| Type111 ID source | Honda unknown; MHI2 candidate | Unknown | Unknown | Unknown | Synthetic only |
| Type110 ID and KDF | Honda-confirmed for Type110 | No presumed reuse | Yes for Type110 | No API found | Existing synthetic KDF only |
| Session master for Type111 | Type110 input confirmed; Type111 reuse unknown | Unknown | Type110 path only | No reviewed transfer | Placeholder only |
| Type111 derivation | Honda unknown; MHI2 hypothesis | Unknown | No handler | Unknown | Candidate test only |
| Listener factory/dataPort | Type110 ephemeral listener confirmed; Type111 absent | If Type111 uses TCP | Type110 exists; reusable interface unknown | No API found | Fake allocator |
| Timing/teardown callbacks | Session lifecycle exists; extension callbacks unknown | Yes | ABI unknown | No callbacks found | Synthetic events |
| Error/log path | Stock logging exists; ClarityLink path unknown | Useful | Unknown | Unknown | Bounded events |
| Renderer handoff | Separate ExternalDisplay host, no frame API | For physical output | No known route | No supported handoff | Mock adapter |

## Outputs and gates

Candidate outputs are an optional display descriptor, response copy, separate listener/session handle, isolated security/parser/codec state, owned decoded-frame submission, and bounded status. They may not modify Type110/audio state or report success after candidate setup fails. All Type111 fields remain hypothesis/unknown.

This contract does not prescribe hook mechanism, ABI, offsets, load path, or deployment. Before a no-op integration test, prove reversible jmcs entry and recovery. Before Type111, prove Honda-compatible request/response/security. Before renderer integration, prove host entry and frame handoff.
