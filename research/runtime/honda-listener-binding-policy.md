# Honda listener binding policy — 43T1-PREP2

**Decision: `BIND_POLICY_PARTIAL` before 43T0-D evidence; policy engine is implemented and test-ready.** Module: `evaluate_binding` in `src/claritylink-honda/prep2_runtime.py`.

The engine requires one complete authoritative candidate with interface, unscoped address, family, prefix, matching route interface, route support, phase-reversal support, and `HONDA_CONFIRMED` evidence. It rejects competing candidates, stale/partial/traffic-only evidence, absent routes, invalid prefixes, family mismatches, multicast/unspecified addresses, synthetic or host-only evidence, and all wildcard requests. The future placeholders remain:

```text
BIND_INTERFACE = FROM_43T0D_EVIDENCE
BIND_ADDRESS = FROM_43T0D_EVIDENCE
ADDRESS_FAMILY = FROM_43T0D_EVIDENCE
SCOPE_ID = FROM_43T0D_EVIDENCE_IF_REQUIRED
```

IPv6 link-local requires a scope matching the selected interface. `0.0.0.0` and `::` are rejected. Existing `InterfacePolicy.LOOPBACK_TEST` is used only in host tests; wildcard listeners remain test-only and do not satisfy Honda policy. There is no valid Honda policy object today, so no Honda listener can be prepared.

The engine checks evidence consistency and policy shape; it does not itself observe the Honda interface table or decide whether live reachability succeeds. 43T0-D/D4 is still required, followed by a fresh ECC review. Host listener behavior is `LAB_HOST_RUNTIME_CONFIRMED` only.
