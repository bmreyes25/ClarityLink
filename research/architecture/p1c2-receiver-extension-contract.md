# P1-C2 — contract required for a stock-preserving receiver extension

This is an evidence gate for evaluating a future **existing supported** interface. It does not describe a callable interface found in the reviewed Honda artifacts or authorize implementing one inside the stock receiver. See [audit](p1c2-jmcs-additive-extension-audit.md) and [candidate matrix](p1c2-type111-extension-matrix.json).

| Requirement | Proof needed from stock producer and external consumer | Current result |
|---|---|---|
| Entry/admission | Named Binder/socket/module endpoint, stable ABI, caller permission and registration timing. | None shown for authenticated content. |
| Session association | Stable session ID/handle with generation and close semantics, avoiding stale/reused identifiers. | `AirPlayReceiverSessionRef` is a process-local pointer. |
| Negotiation | Authorized capability contribution before `/info`, Type111 SETUP callback with request fields and an accepted response entry. | Stock supplies one main display; Type111 is skipped. No external hook. |
| Security | Explicit least-privilege per-stream context or receiver-mediated encrypted frame delivery, with authentication owner retained by Honda. | Keys/CTR state remain in `jmcs`; no handoff. Credentials must not be extracted. |
| Media delivery | Listener/accepted FD or authenticated frame/metadata stream, ownership and backpressure defined. | Internal Type110 listener and sink only. |
| Type110 isolation | Independent consumer whose registration cannot replace, outrank or alter stock screen/audio/auth callbacks. | `devmgr` is ranked single-winner; proxy registration is singleton. |
| Lifecycle | Session create, stream start, stop, failure, device detach and cleanup notifications with exactly defined resource owner. | Only process-local callbacks found. |
| Integrity and compatibility | Provenanced firmware identity, ARM32/API17 compatible calling contract, versioned request/response, bounded error behavior. | Original two artifact hashes verified; extension contract absent. |

If such a contract is found, ClarityLink can reuse its negotiation model, transport, lifecycle, H.264 receiver, and Android surface adapter. Integration still needs a fresh review of permissions, security ownership, callback lifetime and Type110 behavior before implementation or any live operation. A generic loader, local exported symbol, internal mutable plist, or navigation boolean callback fails this contract. No replacement, interposition, credential extraction, or stock binary modification is proposed.
