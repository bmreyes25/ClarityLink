# Step 38 contract checklist — Type111 SETUP and security

This is a research entry checklist, not a live-hook or implementation ABI.

## Static entry points to analyze

| Function/path | Address/evidence | Step 38 question |
|---|---|---|
| `_connectionHandleMessage` -> `AirPlayReceiverSessionSetup` | `0x28af6a` call; Setup `0x2854e0` | request/session/response ownership and exact dispatch context |
| Stream array element/type extraction | `CFArrayGetTypedValueAtIndex` near `0x2858f4`; `CFDictionaryGetInt64` `0x28590e` | mixed-entry order, duplicates, unknown Type111 skip semantics |
| Type110 per-entry setup | Setup branch around `0x28606e`, direct helper call at `0x28609c` | what state/listener/security fields stock mutates |
| Unsupported-type branch | `0x2861f6` then index increment/continue `0x286220` | whether Type111-only/mixed request yields success, omission, or error |
| Listener and response | `ServerSocketOpen` call `0x286124`; `dataPort` insert `0x286160`; `_AddResponseStream` `0x284db8` | socket ownership, append order, cleanup on later failure |
| Type110 session teardown | `_ScreenTearDown` `0x284628`; Setup teardown helper `0x2852ec` | rollback coverage and partial-success semantics |
| Setup result serialization | `_requestSendPlistResponse` `0x289f60`, call `0x28afba` | exact response merge window and CF ownership |
| Screen key derivation/security | `AirPlay_DeriveAESKeySHA512ForScreen`; SetSecurityInfo; `AES_CTR_Init` | exact serialization, lifetimes, ID width/byte order, Type111 compatibility |

## Contract ledger

| Contract element | Current classification | Evidence / missing proof |
|---|---|---|
| Incoming request root and `streams[]` list | **KNOWN FROM HONDA** | Setup request plist; per-entry type extraction at `0x28590e` |
| Type111 stream dictionary fields | **UNKNOWN** | Honda has no Type111 handler; MHI2/xcertplay are prior art only |
| `streamConnectionID` meaning and type | **KNOWN FROM HONDA for Type110; UNKNOWN for Type111** | Type110 participates in key derivation; Type111 dataflow not reached |
| Session master security input | **KNOWN FROM HONDA for Type110; UNKNOWN for Type111** | Type110 SetSecurityInfo path only |
| Screen key/IV derivation | **KNOWN FROM HONDA for Type110; UNKNOWN for Type111 reuse** | exact Type110 derivation and AES-CTR model in `honda-screen-crypto.md` |
| Filtered stock delegation of 100/101/110 | **UNKNOWN** | architecture candidate only; no interposer |
| Secondary listener allocation and port | **KNOWN FROM HONDA for Type110; UNKNOWN for Type111 ownership** | Type110 `ServerSocketOpen` and response dataPort path |
| Type111 response dictionary keys/values | **UNKNOWN** | MHI2/xcertplay prior art; Honda skips Type111 case |
| Response merge and serialization | **KNOWN FROM HONDA for Setup response ownership; UNKNOWN for safe mutation** | same response pointer is serialized synchronously; thread/reentrancy unknown |
| Session teardown and listener close | **KNOWN FROM HONDA for stock Type110 lifecycle; UNKNOWN for mixed Type111 cleanup** | `_ScreenTearDown` / `AirPlayReceiverSessionTearDown` require complete path trace |
| Mixed-stream failure semantics | **UNKNOWN** | Type111 branch logs and continues; Type110 side effects/rollback depend on order |
| Primary Type110 preservation | **KNOWN FROM HONDA baseline; future interposer invariant** | preserve request entry and stock response without mutation |

## Required Step 38 output

Before any Type111 Setup handler is implemented, record input/output CF object ownership, per-entry success/error accumulation, when listener creation occurs, whether a later invalid entry rolls back earlier Type110 mutations, and how teardown closes a secondary listener. Build synthetic request cases for Type111-only, Type110+111 in both orders, supported audio+111, duplicate 111, and injected secondary allocation failure. Do not run them against a vehicle.
