# Step 47 — Type111 architecture comparison and offline transaction model

**Decision:** stock-first control with an independently owned Type111 media lifecycle remains the strongest offline design candidate. **HONDA TYPE111 INTEGRATION — NOT PROVEN.** The synthetic transaction experiment passed; no Honda receiver code was run.

## Scope and evidence boundary

This report records the engineering conclusion and synthetic test outcomes from public source and project-owned synthetic models. It contains no proprietary firmware-derived addresses or fingerprints, private capture references, or private local paths.

No Honda receiver or vehicle was contacted, and no Honda code or firmware was executed or changed for this checkpoint. These shim regressions use synthetic memory and do not read a Honda binary. No phone or ADB operation, deployment artifact change, or GitHub workflow change was made.

## Architecture comparison

These public source revisions show two relevant design families:

- [MHI2 AltScreen at `f4d4da9`](https://github.com/harman-f/mhi2_altscreen_carplay/tree/f4d4da979627c00c3ed617ac67853adb7f428839), particularly its [Gen2 implementation](https://github.com/harman-f/mhi2_altscreen_carplay/blob/f4d4da979627c00c3ed617ac67853adb7f428839/modules/carplay/source/altscreen111-gen2/libaltscreen111_gen2.c), and [MHI2 altScreen at `6ff7ca4`](https://github.com/joeyQuery/MHI2-altScreen/tree/6ff7ca40107fb27126fef7fb0c5023252d610871), particularly its [Gen2 source](https://github.com/joeyQuery/MHI2-altScreen/blob/6ff7ca40107fb27126fef7fb0c5023252d610871/src/gen2-audi/libaltscreen111_gen2.c), show stock-first control paths with separately owned Type111 media lifecycle code.
- [MIB2Q CarPlay RGI at `21f5016`](https://github.com/luka-dev/mib2q-carplay-rgi/tree/21f501611b0b28dbdeb2849e8443ce90ec9517ff) uses an [independent hook/receiver path](https://github.com/luka-dev/mib2q-carplay-rgi/blob/21f501611b0b28dbdeb2849e8443ce90ec9517ff/hook/altscreen/altscreen_hook.c); [MHI2Q AltScreen at `652448d`](https://github.com/yuedizhibo/MHI2Q-CarPlay-AltScreen/tree/652448ddc1d5c9dd2f4a673b9950cf3c6a9195a4) describes a [private stock-machinery path](https://github.com/yuedizhibo/MHI2Q-CarPlay-AltScreen/blob/652448ddc1d5c9dd2f4a673b9950cf3c6a9195a4/Toolbox/carplay_alt_screen/src/p1404_private111_backend.h) with fail-closed target assumptions.

[DiPlay at `615b32c`](https://github.com/shihabal3amri/DiPlay/tree/615b32ce0b40cd0b99ce94ba23a512001553684f) and [xcertplay at `1298fb3`](https://github.com/shilapi/xcertplay/tree/1298fb35e29ee30e7bd849cb0e751b52aa22a13f) are independent receiver applications with [documented cluster output](https://github.com/shihabal3amri/DiPlay/blob/615b32ce0b40cd0b99ce94ba23a512001553684f/docs/DILINK4_CLUSTER.md) and [separate display pages](https://github.com/shilapi/xcertplay/blob/1298fb35e29ee30e7bd849cb0e751b52aa22a13f/common/src/main/assets/carplay-display.html), respectively. Their platform and receiver ownership differ from an extension to an existing Honda receiver. Public source evidence from these projects is useful for architecture comparison only; it does not establish behavior on Honda hardware.

The reviewed source set does not establish a safe, additive entry into the Honda receiver with authenticated stream-key authority and a paired cleanup path. The stock-first design is therefore a candidate for offline work, not an integration recommendation for vehicle deployment.

## Offline transaction experiment

The Thumb shim tests run compiled project code in Unicorn against synthetic request, response, and session memory. They do not read or require Honda binaries, so they run in the public test environment without private artifacts. The generation and listener are activated before the stock serializer can observe the Type111 entry. If activation fails, the response is restored to Type110-only before the serializer runs. If serialization fails after activation, the owned resources are rolled back.

The cases cover successful staging and serialization, listener preparation failure, activation failure, serializer failure after activation, and gate-release failure after serialization. They assert that the synthetic request and Type110 descriptor remain byte-identical, the stock serializer boundary is invoked once, its return value is preserved, and no failed post-serialization gate release retracts the already advertised listener. The synthetic service contract consumes the gate lease on both successful and failed release; a reported cleanup error leaves the response and active listener intact while returning an internal cleanup status. A real service must satisfy this consume-on-failure contract before any integration claim; no live service or Honda runtime was tested here. This does not exercise Honda's native response objects or prove runtime ABI compatibility.

The response-delivery ownership model covers a separate boundary: parent HTTP response serialization, retryable writes, unknown output progress, terminal failures, transport completion, generation fencing, and Type111 resource cleanup. Write-count arguments are per-attempt deltas; the model's output field is cumulative, and when progress is unknown the exact count is unset while the offset retains only its last confirmed lower bound. If cleanup closes the listener before sending begins, the response is terminally fenced as known no-output; cleanup during an in-flight write fences retries as delivery unknown, even if the last confirmed offset was zero. After local transport completion, HTTP connection finalization preserves the accepted media socket, which remains until session teardown or other child cleanup. Project failure, serialization failure, incomplete connection finalization, terminal send failure, or parent session teardown releases the child as appropriate. These are model results; local transport completion does not prove protocol-level peer acceptance.

## Evidence classification

| Result | Classification | Outcome |
|---|---|---|
| Public-source architecture comparison | Public source review | Supports the stock-first design as an offline candidate; does not establish Honda compatibility. |
| Compiled shim under Unicorn | MODEL_ONLY | Synthetic transaction cases preserve Type110 request/descriptor bytes and exercise commit or rollback. |
| Python serialization and response-delivery contracts | MODEL_ONLY | Confirms modeled state transitions and cleanup boundaries, not Honda-native ownership. |
| Running Honda receiver instructions or loading ClarityLink into the receiver | Honda binary execution | NOT RUN. |
| Receiver behavior on a Honda or phone | Vehicle/device runtime | NOT RUN. |

## Focused verification

The exact four focused modules run on the current worktree were:

```text
python -m pytest -q tests/negotiation/test_response_delivery_ownership.py tests/negotiation/test_thumb_setup_shim.py tests/negotiation/test_type111_setup_contract.py tests/negotiation/test_existing_call_wrapper_contract.py
111 passed
```

The configured local test environment also ran `tests/native/test_native_setup_txn_host.py`, including its concurrency, malformed-input, ASan/UBSan, and TSan checks: **114 passed total** across the four focused modules and this host-native module. Python compilation checks and `git diff --check` passed. No Honda binary artifact was used.

## Result and remaining proof obligation

- **Offline model experiment: PASS.** The synthetic Type110 request and descriptor remain unchanged through modeled Type111 success and failure paths.
- **Delivery model: PASS.** Serialization history is kept distinct from transport outcome and Type111 child cleanup.
- **Honda integration: NOT PROVEN / NO-GO.** No evidence in this experiment establishes an additive same-session receiver entry, key authority, or paired finalizer.
- `safeForHonda() == false` remains unchanged.

The next proof obligation is an authorized receiver interface or new documentary evidence establishing an additive same-session control entry with authenticated stream-key authority and a paired cleanup path. Display attachment remains a separate unresolved requirement.
