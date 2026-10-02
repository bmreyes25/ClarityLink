# SYNTHETIC GOLDEN FIXTURE — NO HONDA CAPTURE
# Step 43T0-D — read-only Honda network delta analysis

Capture status: **CAPTURE_VALID**. Identity: **IDENTITY_MATCH**.
Starting HEAD recorded by collector: `aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa`. Honda contacted by target command: YES; ADB used: YES. Target writes: **0** under the reviewed command contract. Root/su: **NO**.

Phases completed: baseline, connected, post-disconnect. Command count: 23. Final stock sanity: collector SUCCESS. CAR-OFF boundary: operator must issue the exact runbook message after collector exit.

## Interface, address, route, and 40E findings

Candidate state: SINGLE_STRONG_CANDIDATE; interface: cp0; family: IPv6. IPv4 and IPv6 exact addresses are withheld. Route policy: YES. 40E correlation: stock CarPlay IPv6 link-local global socket rows; process ownership remains blocked.

## G11

| Gate | Result |
|---|---|
| G11_A | YES_OBSERVED |
| G11_B | YES_OBSERVED |
| G11_C | IPv6 |
| G11_D | YES |
| G11_E | NO / READ_BLOCKED_WITHOUT_PRIVILEGE |
| G11_F | NO |

Candidate binding policy: {"address_family": "IPv6", "evidence_class": "HONDA_OBSERVED_NETWORK_POLICY_INPUT", "interface_name": "cp0", "local_address": "WITHHELD", "route_present": true, "scope_id_required": true, "wildcard_binding_recommended": false}.

## Boundaries

Reversibility: phase reversal observed. Privacy: SANITIZED. Limitations: G11-E and G11-F unresolved by observational capture. Type111 and listener reachability untested.

Next recommendation: **43T1-PREP — offline reversible RAM-only listener/attachment readiness design**. No vehicle action follows automatically.
