# R5Y — future adapter contract

**No HondaReceiverAdapter implementation exists.** The name is a documentation concept only: `NO HONDA IMPLEMENTATION · REQUIRES NEW HONDA_STATIC EVIDENCE · NOT AUTHORIZED FOR VEHICLE USE`. Current executable providers are symbolic mocks. Adding a host fake should preserve the `r5y_receiver_core` tests; a target adapter would need a separate future proposal, evidence, security/safety review, and authorization.

| Adapter | Input contract | Output contract | Ownership and lifetime | Failure semantics | Evidence required before any target implementation |
|---|---|---|---|---|---|
| Receiver entry | An observed receiver session event | A scoped model session label | External owner must retain stock path; model owns no target resource | Reject missing/ambiguous event | Additive or separately approved same-session entry, absent under R3C |
| Session identity | Evidence-backed session identity | Monotonic `SessionGeneration` | Cannot use a reusable pointer alone | Reject collision/stale event | Stable real identity, create/finalize pairing |
| Setup request | External Setup object | Validated `SetupRequest` | Borrowed input; model stores invented values | Reject unknown shape before child allocation | Actual Honda request object/schema and safe observation |
| Setup response | Frozen `SetupResponse` | External response mutation/commit result | Target ownership outside sandbox | Abort on serialization/ownership failure | Mutable pre-serialization response and schema/ownership proof |
| Listener provider | `SessionGeneration` | `ListenerHandle` equivalent | Exactly one child owner until close | No partial resource survives failure | Listener ABI, binding, reachability, cleanup |
| Security provider | Generation and future verified mode | Context equivalent | Destroyed with child | Unknown mode fails closed | Honda Type111 security/framing and lawful credentials |
| Decoder provider | Validated frame model | Decoded frame equivalent | Child-scoped | Failure clears sink and child | Compatible media path and decoder output contract |
| Display provider | Decoded frame model | Display sink equivalent | Child-scoped, clear on loss/teardown | Never leave stale content | Display 1 admission, safe area, warnings and z-order |
| Lifecycle adapter | Exact generation | Closure event | Must cover normal and exceptional paths | Stale event cannot close newer child | Honda lifecycle/finalizer ownership and independent cleanup |

The `ReceiverEntryAdapter`, `SetupRequestAdapter`, `SetupResponseAdapter`, `SessionIdentityAdapter`, `ListenerProvider`, `SecurityProvider`, `DecoderProvider`, `DisplayProvider`, and `LifecycleAdapter` Protocols mark these seams. Only the four symbolic provider Protocols are exercised by the current facade. R3C still controls runtime NO-GO; defining an interface does not reopen it.
