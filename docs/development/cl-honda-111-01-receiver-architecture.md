# CL-HONDA-111-01 / M3 — Minimum Type111 receiver extension: architecture decision

Offline design. No Honda integration is enabled or authorized. `safeForHonda() == false`. Inputs: the [evidence map](../../research/honda/cl-honda-111-01-evidence-map.md) and the [receiver admission matrix](../../research/honda/cl-honda-111-01-receiver-admission-matrix.md).

## 1. Constraints that shape the choice

- **No additional hardware.** An independent second receiver, a CPC200/LIVI Link, an extra MFi device or an aftermarket unit are excluded. LIVI is not part of this architecture; an external LIVI bridge would not supply Honda session authority, and nothing here relies on one.
- **The Honda owns the only authenticated session.** The parent session, its master material and the Setup transaction exist only inside the factory process. ClarityLink must not extract credentials, emulate an accessory, copy session secrets to another process, guess Type111 keys from Type110 material, or bypass verification.
- **Type110 is factory-owned and must not change.** The screen object's CTR context, the proxy's single registration, the `streams[]` teardown loop and the response array are all Type110 state.
- **No deployable hook is authorized.** Candidates that need a hook are scored as designs, not as plans.

## 2. Candidates

### Candidate 1 — Factory-owned Type111 child stream (receiver-resident extension)

The factory session stays the sole parent authority. Code resident in the receiver process calls stock Setup first with the original request, then, only on success and only if the request carried a Type111 entry, creates a separate child: its own listener and data port, its own key and CTR context from an authorization the parent grants, its own decoder, its own teardown owner. It appends a project entry to a *copy* of the stock response. Type110 is never touched. On any child failure the stock response is returned unchanged and only child state is rolled back.

This is the shape every working external implementation has (Project B, Project C), and the Honda ownership ledger supports every step: the CF append and release rules, the listener pattern and the KDF helper all exist in `jmcs`.

### Candidate 2 — Supported in-process stream-consumer delegate

A documented callback that hands a consumer only stream-specific content or an opaque child handle, with the parent keeping authentication and revocation. **No such delegate, registration key, Binder method or exported interface exists** in the reviewed Honda surface. The destroyed-session event that does exist is one global callback slot with no session identity, which cannot carry per-child revocation. Classified `UNSUPPORTED`; it is not made real by a reachable internal function.

### Candidate 3 — Factory receiver receives and decodes; a separate ClarityLink component consumes decoded output

Lets the factory process keep the whole protected path, which narrows the security boundary. It fails on two facts: the proxy exposes a **single** screen registration (a second returns "already registered"), so a second decoded-frame sink cannot be registered through the platform binding; and no export of decoded frames exists. It also moves the decode into the factory process anyway, so it still needs Candidate 1's resident code plus a new frame channel.

### Candidate 4 — Other software-only methods on existing hardware

| Variant | Mechanism | Assessment |
|---|---|---|
| 4a | `LD_PRELOAD` or inline interposition of `jmcs` (the Audi pattern) | Technically the same shape as Candidate 1. Requires modifying factory process startup or code. Not authorized; classified as a private, unsupported mechanism. |
| 4b | Xposed injection into a Honda process | HondaHack's mechanism. It reaches the *display* host, not the receiver, and carries no caller authorization. |
| 4c | Network proxy for `/info` and Setup | Needs the phone to route through ClarityLink, key material the proxy cannot get, and a frame handoff that does not exist. Evidence rates it below `jmcs`. |
| 4d | Private Binder replay | Prohibited. |
| 4e | Independent second receiver | Excluded by the no-hardware constraint and needs its own authentication. |

## 3. Scoring

Scale: 0 = contradicted or absent, 1 = weak, 2 = partial, 3 = strong. "Evidence" means the strength of preserved Honda evidence for that architecture, not a verdict on legitimacy.

| Criterion | C1 resident child | C2 delegate | C3 decode, external sink | C4a preload hook | C4b Xposed | C4c proxy |
|---|---|---|---|---|---|---|
| Honda source evidence | 3 | 0 | 1 | 3 | 1 (display side only) | 1 |
| Session ownership stays with factory | 3 | 3 | 3 | 3 | 0 (no receiver access) | 0 |
| Authentication compatibility | 2 (KDF lead; Type111 unproven) | 2 | 2 | 2 | 0 | 0 |
| Type110 continuity | 2 (isolation by design, unproven live) | 2 | 1 | 2 | n/a | 1 |
| Implementation complexity (3 = low) | 1 | 3 if it existed | 1 | 1 | 2 | 0 |
| API17 / ARMv7 feasibility | 2 (ARMv7 native; Thumb/ARM veneers known) | 3 | 1 | 2 | 2 | 1 |
| Reversibility | 1 (process-resident) | 3 | 1 | 1 | 1 | 2 |
| Display compatibility | 2 (frame channel still needed) | 2 | 1 | 2 | 1 | 0 |
| Security reviewability | 2 (small, bounded) | 3 | 1 | 2 | 0 | 0 |
| Factory safety | 1 | 3 | 1 | 1 | 1 | 1 |
| Missing external evidence (3 = least missing) | 1 | 0 (interface absent) | 1 | 1 | 1 | 0 |
| **Total** | **20** | **24 (hypothetical)** | **14** | **20** | **9** | **6** |

C2 scores highest *because* it is the safe ideal, and it does not exist. That is the finding: the best-scoring supported design is unavailable, and the best-scoring available design (C1, whether by C4a or any other resident mechanism) is **unauthorized**.

## 4. Decision

- **Preferred research architecture: Candidate 1 (receiver-resident, stock-first, additive child).** Justified by Honda source evidence for every step it needs and by two independent shipped implementations of the same shape. It is *not* a deployment plan: its entry point is C4a-class interposition, and no supported boundary exists.
- **Candidate 2 is the goal state.** If the factory code's owner ever provides a delegate or a registration contract, ClarityLink's existing consumer-side models are what plug into it.
- **Candidate 3 is rejected** on the singleton proxy and the absent export.
- **C4b, C4c, C4d, C4e are rejected** for the receiver side.

This matches the brief's final-verdict class **B**: a credible software-only architecture exists, important support and security contracts remain unverified, Honda integration stays disabled.

## 5. The child-stream contract ClarityLink can pin down now

The contract is expressed once, on the consumer side, so any future provider must meet it. All properties are enforced in code and tests (see the [display integration document](cl-honda-111-01-type111-display-integration.md)).

| Property | Rule |
|---|---|
| Parent binding | A child exists only under one parent authority, one parent generation and one stream identity. |
| Capability | The child holds an **opaque** capability, never session secrets. It can ask the parent to open, can be revoked, and cannot export keys. |
| Single use | A grant opens at most one child. A revoked or consumed grant cannot be reused. |
| Parent loss | Parent teardown revokes the child and everything downstream of it; a child can never outlive its parent. |
| Independent close | Closing the child never touches parent or Type110 state. |
| Type isolation | Child frames never share a queue, generation, counter or security context with Type110. |
| Fresh authority | Any restart needs a strictly greater generation and a new grant. |
| Fail closed | Missing, mismatched, expired or unattested authority denies. There is no default profile and no default KDF. |
| No synthetic masquerade | A grant created from synthetic inputs is labelled and cannot satisfy a non-synthetic check. |

## 6. GO / NO-GO conditions

| Condition | Today |
|---|---|
| G1. The owner of the factory code supports an extension boundary (documented hook, delegate or registration) **or** the user provides separate, written authorization for a specific private mechanism with independent review. | **NO-GO** (neither exists) |
| G2. The Type111 `/info` descriptor schema, feature tokens and SETUP request/response shapes are known from a lawful, authorized phone-to-Honda observation. | **NO-GO** (`UNKNOWN`) |
| G3. The Type111 key-derivation inputs and profile are known, and the parent authorizes the child to use them. | **NO-GO** (`UNKNOWN`) |
| G4. VideoConfig protection (clear versus within the CTR stream) is known for Honda Type111. | **NO-GO** (`UNKNOWN`, conflicting external evidence) |
| G5. A decoded-frame sink for a second stream exists that does not displace the proxy's single registration. | **NO-GO** (singleton) |
| G6. Type110 continuity is demonstrated with a real simultaneous session. | **NO-GO** (never tested) |
| G7. Independent security review of the child authority and its failure paths. | **NO-GO** (not performed) |

All seven must be GO before any active mechanism is proposed for authorization. One is not enough, and offline software cannot flip any of them.

## 7. What this campaign implements

The consumer-side contract (section 5) and the display-side pane contract, using the existing `Receiver`, `FrameGate` and cluster models, with synthetic data only. It adds no KDF, no profile, no attestation and no Honda call. The CL-AUTH-01 trust classes (PR #78) are compatible with this contract (a child grant would sit under an `ATTESTED` parent, which is unreachable today) but this branch does not depend on that unmerged work.
