# CL-54B Control/SETUP fail-closed gate

Date: 2026-11-08
Task: `CL-54B-CONTROL-SETUP-GATE`
Base: native checkpoint `a945ead50a4cd36db935b7865a15bb88f6a1f56f`

## Question and implementation

**Question:** Can the existing offline Type111 setup transaction exercise Type111 lifecycle behavior without representing an unauthenticated listener as a Honda-accepted stream?

**Change:** `Type111SetupContract` now rejects Type111 by default with `type111_authority_unavailable` before listener allocation or generation creation. It passes a copy of the unchanged stock response through the stock serializer once, reports `TYPE111_DISABLED_AUTHORITY_UNKNOWN`, and returns no Type111 port, listener, or generation. Factory Type110-only requests still use the normal transaction path. Existing Type111 lifecycle tests and the synthetic lab explicitly opt in using `enable_synthetic_type111_for_tests`; the typed `SecurityMode` is propagated through the stock-first adapter, and the lab accepts its synthetic stream only when the result is tagged `SYNTHETIC_TEST_ONLY`.

The adapter is a host-side transaction model. It has no binding to Honda's receiver session, Control SETUP implementation, authenticated transport, or stream dispatcher. The opt-in is for offline tests and the synthetic lab only; it permits the exact deterministic test allocator and the host `RealListenerAllocator` configured with `InterfaceKind.LOOPBACK_TEST`. The type and policy are checked at construction and immediately before reservation. The stock-first delegator passes its own default-off test flag into the contract before setup, so an unapproved synthetic result is never listener-allocated or serialized. `security_mode` describes execution/evidence context, not success: consumers must also check `committed`. These checks are not a security boundary, and neither flag is Honda feature authorization.

## Evidence boundary

The three protocol stages remain separate:

1. **`/info` advertisement:** the native checkpoint builds an offline auxiliary descriptor candidate while preserving Honda's primary descriptor. The Honda-specific callback binding and phone acceptance are unproven.
2. **Control SETUP negotiation:** the recovered Honda evidence does not establish its request/response capability schema or an accepted auxiliary-feature state that persists into stream SETUP. The clean-room external profile in `src/claritylink-negotiation/external_alt_screen.py` records prior-art fields such as `enabledFeatures` and `altScreen`; these are not established Honda fields and are not emitted by this change. Absence of a literal in a binary/report is not proof that no runtime capability path exists.
3. **Type111 media SETUP:** the Honda SETUP analysis says type 111 is skipped by the examined dispatcher; it does not supply a Honda Type111 response schema or authenticated stream authority. A synthetic listener is therefore insufficient grounds for successful SETUP.

Supporting preserved evidence includes `step-reports/42a-type111-display-stream-correlation.md`, `research/carplay/honda-info-type111-differential.md`, `research/runtime/43t1-r3c-stream-dispatch-extension-audit.md`, and the prior-art-only external profile. Honda Type110 security and stream behavior remain Type110 evidence only.

## Test result

Executed from the scoped worktree:

```text
pytest -q tests/negotiation/test_type111_setup_contract.py \
  tests/negotiation/test_setup_contract.py \
  tests/jmcs/test_stream_dispatch.py \
  tests/negotiation/test_thumb_setup_shim.py \
  tests/native/test_native_setup_txn_host.py \
  tests/jmcs/test_cl_imp_06_stock_delegation.py \
  tests/integration/test_cl_imp_11_dual_display_lab.py
137 passed, 21 subtests passed
```

The inherited native advertisement helper was also revalidated with the
configured Studio Android NDK:

```text
ANDROID_NDK_HOME=<Studio NDK r23c> CL_NATIVE_REQUIRE_TARGET=1 pytest -q -rs tests/jmcs/native
3 passed, 0 skipped
```

This includes a host CoreFoundation harness, API17 ARMv7/Thumb ABI checks, and
ARM execution under Unicorn with synthetic CF callbacks. It verifies the
project-owned helper's isolated behavior only; it does not execute Honda's
CFLite, bind the helper to the `jmcs` property handler, or validate iPhone
acceptance.

Coverage confirms stock-envelope validation before Type111 augmentation, unchanged original stock serialization once on Type111 rejection and Type110-only requests (including a copied malformed non-mapping response), specific malformed request diagnostics before listener work, consistent Type111 classification across the transaction and delegator, default rejection for mixed 110/111 requests, fail-open stock behavior when the listener allocator is absent, stock-only Type110 responses through the lab, including the Type111-disabled fallback, no default listener/generation allocation, Type110 continuity, exact synthetic allocator checks before allocation, pre-serialization rejection of a synthetic child unless both test flags opt in, candidate and factory serializer-mutation rejection with original snapshots preserved, serializer-invalid-result fallback preserving the stock snapshot, Type111 candidate serialization failure followed by stock-only serialization, activation failure followed by stock-only serialization, cleanup-exception token retry, rollback/generation paths, parent-loss cleanup even when a later request acquired no child generation, stale-transaction isolation from newer parent generations, mismatched-primary revocation refusal, parent-owner state revocation, response validation scoped to the SETUP request that produced it, and Type111 rollback after a rejected or mismatched lab SETUP response. Malformed stock data is passed unchanged to the original serializer; the delegator preserves its specific error and marks `primary_preserved=false`, so it does not describe that malformed result as healthy. These are offline model results, not Honda-native or iPhone negotiation results.

## Readiness and next experiment

No Control SETUP field is accepted or advertised by this adapter. The next executable native task needs the actual Honda Control SETUP dataflow and the state handoff from accepted features to SETUP dispatch. Until that contract, receiver-owned per-stream authentication, and a ready independent transport are established, Type111 stays disabled in the default path. Independent review identified a cached optional import, parent-loss cleanup for transactions without a child generation, and serializer behavior for non-mapping stock input. A missing optional listener module is not cached, while a successful type lookup is cached; parent loss destroys project-owned children only for the still-current parent; stale setup work cannot tear down a newer parent and cleanup uses an exact generation token; fallback preserves specific request errors and invokes the stock serializer once with a deep-copied non-mapping input where possible. A failure copying the serializer candidate leaves the invocation count at zero so the stock fallback gets its one call. If stock data itself is not deepcopy-compatible, the stock serializer still receives the original mapping once; the model returns no project snapshot and retains the original gate error while exposing `fallback_error_code=stock_response_copy_failed`, with Type111 disabled. The exact task scope also covers delegation/demo callers, malformed-request handling, shared request classification, listener policy checks, synthetic status propagation, default-off delegation, and explicit lab opt-in.

## Review-driven hardening

Independent review found that a failed Type111 candidate serialization could prevent the stock-only Type110 response from being serialized, and that activation failure returned a factory snapshot without re-running the stock serializer. The adapter now rolls back the exact Type111 generation and retries response construction from an unchanged factory snapshot. `candidate_serializer_result` and `serializer_result` separately record the candidate attempt and final stock-only response result. The diagnostic distinguishes Type111 candidate serialization failure from a failed stock serializer retry. Tests cover a failing Type111 candidate with a successful stock-only Type110 serialization, and the inverse where both fail. The serializer contract remains an offline local response-construction probe; it cannot write to a control channel and does not prove Honda serialization behavior.

Cleanup now preserves the exact generation token when the first cleanup attempt raises, retries it at the delegator boundary, checks the generation phase when cleanup returns false, and reports unresolved cleanup as `type111_cleanup_failed`. Parent loss is still handled if a child cleanup retry fails; a failed parent cleanup remains explicitly retryable by session revocation. A failed post-serializer snapshot copy retains the pre-serializer stock snapshot when available. The serializer callback is documented as a local response-construction probe with no network side effects; an actual Honda integration still needs a verified response-commit boundary.

The optional listener-class lookup is no longer cached, so a missing or reloaded host module cannot leave a stale allocator-type result. When an outer synthetic-mode gate rolls back an already committed child, the returned transaction snapshot now clears its listener/port and committed markers after successful cleanup. Fallback serializer errors now prevent the lab from claiming healthy stock setup, and an unaccepted or mismatched mock SETUP response tears down the project child. The mock response validator is reset and associated with each request, and session revocation refuses a mismatched primary generation. These fixes do not establish Honda Control SETUP negotiation or a Type111 security/transport handoff.

No vehicle, firmware, startup configuration, archived receiver bytes, or live iPhone session was touched. This offline checkpoint was published as `WIP_UNVERIFIED` on `codex/cl-54b-control-setup` at `4c3c86b39542b9d5f18ce5d498590e9cbf3aa7e4`; the publisher verified the same remote SHA and did not open a PR. Exact-scope independent review remains pending, so the WIP publication is not an approval or a reviewed PR checkpoint. The next publication step is an eligible exact-scope review followed by a VERIFIED stacked PR if the review and release checks pass.
