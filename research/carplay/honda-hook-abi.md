# Honda Setup response hook ABI (recovered call site)

## Setup call

`_connectionHandleMessage` at `0x28af6a–0x28af72` calls `AirPlayReceiverSessionSetup` (`0x2854e0`):

```text
r0 = receiver session object, loaded from [r10 + 0xf4]
r1 = request CF dictionary
r2 = pointer to response slot at caller sp + 0x54
r0 on return = OSStatus
```

The response slot is read only after a zero status. Setup writes the response dictionary through its saved `r2` at `0x286260`. The caller immediately installs session properties, passes the same response pointer to `_requestSendPlistResponse` at `0x28afba`, and releases it at `0x28b052` after serialization. AAPCS32 ARM/Thumb is used. The actual machine call-site ABI and caller cleanup are recovered even though the ELF lacks formal parameter DIEs.

## Candidate windows

| Candidate | Stock first | Response available | Mutable | Ownership understood | Primary behavior preserved | Assessment |
|---|---|---|---|---|---|---|
| A. Setup wrapper | yes if it delegates to original | through out pointer on return | yes before serializer | yes for this caller path | possible, untested | medium/high risk: full indirect call population and reentrancy unknown |
| B. caller after Setup | yes | yes, `sp+0x54` | yes until helper call | yes, +1 caller ownership | best structural fit; can preserve existing primary entry | **smallest structural candidate; live-hook feasibility remains unknown** |
| C. pre-serializer wrapper | stock response already built | yes | yes | caller owns it | possible | wrapper target known, but changes all plist responses unless narrowly gated by request/context |
| D. response-builder helper `_AddResponseStream` | called by stock | response and new entry available | yes | CF collection semantics plausible | unknown | broad internal ABI/request selection and protocol semantics unknown |

The Setup return path gives the latest evidenced point with the stock response complete and serializer not yet started: immediately after the call at `0x28af72`, before `_requestSendPlistResponse` at `0x28afba`. This is a candidate, not a safe hook decision. Thread/reentrancy details, whether Setup's output callback has side effects relevant to ordering, Type-111 requirements, and display capability negotiation remain unresolved.

Appending to the mutable CFArray uses normal CF retain semantics: the primary entry object/value is not rewritten by append, and array ordering places the new value after the existing one. The offline fixture separately asserts primary-field preservation/order, but this does not prove serializer acceptance or phone behavior.

## Step 39 gate model and remaining ABI evidence

The host gate uses exact `jmcs` SHA-256 `cbc7ba881648fb8ffdfcc4c1100a028345c37134a2ae3b9dff7d76572851c232` as the known binary identity from prior offline analysis. Static notes identify `_requestProcessInfo` around `0x28a018`, its server-info return at `0x28a156`, serializer boundary at `0x28a19c`, and `AirPlayReceiverSessionSetup` at `0x2854e0`.

Step 39 implements only data models for binary/function identity and all-or-nothing group eligibility. Exact entry instruction bytes, register/stack argument contract, ARM/Thumb resume semantics, object retain/release ownership, SessionStart/TearDown safe interception points, and executable prologue fingerprints are not yet populated in code. Do not enable hooks from these addresses alone. Step 40 must revalidate against the exact ELF and disassembly before a harness exists.
