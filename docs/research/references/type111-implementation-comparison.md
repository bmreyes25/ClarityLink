# Type111 implementation comparison

| Question | xcertplay pinned source | ClarityLink evidence | Honda status |
|---|---|---|---|
| Alternate display advertisement | Source constructs an alternate descriptor behind negotiated features | Synthetic Type111 model exists | No genuine Honda Type111 capability/descriptor established |
| SETUP and stream ownership | Type111 gated on negotiation; stream objects keyed by session/type | CL-R4/7 synthetic/API17 lab acceptance | Honda schema, authenticated session authority, and delegation unknown |
| Media path | Local decode or compressed access-unit forwarding | CL-R12 decoded-pixel IPC prototype; handoff-reported performance below | No supported Honda frame input or cluster admission API established |
| Cluster output | Separate view-only web display path | Synthetic display host only | Factory Display 1 ownership/geometry/warning/restoration contract unknown |
| Genuine interoperability | Project author reports hardware use; campaign did not reproduce it | No genuine iPhone run in this campaign | Not proven |

The pasted campaign reports CL-R12-B at 30 seconds: about 1.12 fps, about 30 offered frames, 96.2% drops, p50 869 ms; at 10 minutes: about 1.41 fps, about 30 offered frames, 95.3% drops, p50 613 ms; queue high-water 1 and zero pixel mismatches. These are handoff-reported figures, not present in the checked base reports and not independently re-run here. The root cause remains unknown.

Compressed forwarding may reduce pixel payload copies and IPC volume, but introduces codec/config lifetime, decoder initialization, backpressure, and stale-frame concerns. It merits a separate controlled API17-compatible benchmark after the remaining CL-R12-F performance and reliability gates are addressed. CL-R12-F’s API17 runtime smoke passed, while its declared performance/reliability acceptance remains partial in the current integration-readiness record. Do not replace CL-R7 or claim an improvement without measurements. CL-R4 and CL-R7 remain accepted laboratory results; neither establishes Honda compatibility. CL-R10C's Honda integration NO-GO remains controlling, and `safeForHonda()` remains `false`.
