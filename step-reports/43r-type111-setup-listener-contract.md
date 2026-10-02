# Step 43R — offline Type111 SETUP response/listener contract

**Status:** complete offline. Local verification and hosted Offline CI passed. No runtime or Honda work was performed.

## Starting point and scope

Starting commit: `f9e8e0b9c1656e8d3cddf2c30a0de648c2da2fdb` (`main`, clean worktree). Implementation commit: `60225199ec2d69e093fbe5a49d791760bce3d691`.

This milestone models a project-owned Type111 SETUP extension around the known Honda serializer seam. It is offline only. There was no Honda connection, ADB, vehicle access, binary modification, listener socket, deployment, or media receive/decode path.

## Evidence consumed

The sanitized 43P observation establishes `CURRENT_IOS_LAB_CONFIRMED` that the tested iPhone requested Type111 before Type110, supplied distinct stream IDs, received separate ports, and carried both streams concurrently. The simulator fixture in `research/simulator/43r-type111-first-setup.json` preserves only this structural order with deterministic synthetic IDs and ports. It contains no raw 43P identifier, packet, media, key, or authentication value.

Honda's stock path is `HONDA_CONFIRMED`: `_connectionHandleMessage` reaches `_requestSendPlistResponse` at the direct BL callsite `0x28afba` (`fe f7 d1 ff`) and continues at `0x28afbe`. The response dictionary is mutable before serialization; Honda's stock response builder adds Type110 and its dynamic `dataPort`. The local success predicate is `r0 == 0xc8 && statusOut == 0`. This proves local serialization success only, not phone acceptance.

## Contract architecture

`src/claritylink-negotiation/type111_setup_contract.py` parses every stream by its explicit type and retains request order, screen connection IDs internally, and opaque fields. Type110-only and Type111-only shapes are supported. The parser does not assume array index zero is Type110. The policy for multiple Type111 entries is fail closed. Duplicate Type110/Type111 IDs use the existing `duplicate_stream_connection_id` structured error from the 43Q-A model.

The offline operation order is: validate request and stock response; create a Type111 generation through the 43Q-B `DualScreenLifecycleTwin`; reserve a deterministic fake listener; attach that listener to the exact prepared generation; append only `{type: 111, dataPort: P}` after the untouched stock entries; call the modeled Honda serializer once; activate/commit only when its original success predicate passes. No extra response identity fields are asserted as Honda schema.

The project-owned listener has an identity, deterministic synthetic port, generation owner, listening/closed state, and idempotent close. It creates no OS socket. Resource ownership is attached to the exact 43Q-B child key; teardown of a stopped B generation cannot target a newer B listener. Stock entries and their order are preserved, and the Type111 entry is appended after them. The request order is accepted independently; no claim is made that Honda responses mirror request order.

## Transactions and failure behavior

Malformed requests, duplicate IDs, duplicate Type111 entries, invalid stock response containers, listener allocation/bind/listen failure, invalid port, closed-before-commit listener, response mutation failure, and serializer failure are modeled. Before serialization, project failure rolls back the exact prepared generation and listener, then invokes the stock serializer once with an unchanged stock response when that response is a mapping. On serializer failure, the exact B generation is retired and its listener closed; the serializer's `r0`, `statusOut`, and continuation are retained. Type110 remains outside child ownership and is unchanged. Error results contain structured codes without peer identifiers or secret material.

If the serializer itself raises or returns an invalid result type, no Honda result exists to preserve; this is reported as sanitized project/serializer failure. Invalid stock response objects fail closed and still make at most one serializer invocation with the unchanged original object when preparation has not already invoked it.

## Tests and ECC review

Focused 43R tests: **20 passed**. Combined SETUP/trampoline, Type110 crypto/parser, 43Q-A/43Q-B lifecycle, and project registry regression tests: **101 passed**. Complete configured suite: **349 passed, 4 expected skips**. Self-locator: **3 passed**. Configured simulator checks passed. `git diff --check` passed. 43R documentation links passed a scoped local-link check. A repository-wide markdown scan found pre-existing broken links in unrelated historical reports and vendored/research material; those were left untouched as unrelated scope. Hosted Offline CI passed on implementation commit `60225199` in [run 36966113681](https://github.com/bmreyes25/ClarityLink/actions/runs/36966113681).

ECC security/code review focused on untrusted mapping validation, boolean-as-integer rejection, generation-exact resource ownership, rollback of prepared children, stock-response cloning, exactly-once serializer invocation, result preservation, and sanitized errors. It identified that the existing generic response augmenter carries non-Honda prior-art fields; this contract therefore uses only `type` and `dataPort` while leaving that separate model intact. It also required a narrow PREPARED-generation resource attachment API so listener ownership flows through 43Q-B instead of bypassing its registry. No unresolved high-confidence in-scope finding remains.

## Evidence classifications and limits

- `CURRENT_IOS_LAB_CONFIRMED`: 43P Type111-before-Type110 order, distinct stream IDs/ports, and concurrent streams.
- `HONDA_CONFIRMED`: the Type110 response path and serializer/callsite facts above.
- `LAB_SYNTHETIC_CONFIRMED`: contract behavior established by the offline deterministic tests only.
- `HONDA_UNKNOWN`: whether Honda accepts a modified response; iPhone acceptance of Honda Type111; actual Honda Type111 listener ABI, security mode, crypto, and media behavior.

The 43P PlayPort `MODERN_CHACHA_SCREEN` classification is not used to infer Honda Type111 security. This milestone does not conclude that Honda Type111 works, uses AES, accepts this response, or is ready for runtime patching.

## Next action

Final documentation commit and hosted CI are recorded in Git history. The next bounded milestone is **43S — Honda runtime attachment and Type111 negotiation readiness review**, with explicit go/no-go gates. Do not deploy from this offline result.
