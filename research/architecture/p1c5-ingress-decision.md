# P1-C5 — receiver ingress architecture decision

**Decision: `P1_C5_NO_GO_PENDING_NEW_INTERFACE_EVIDENCE`.** No reviewed candidate supplies a proven, permitted path for authentic active-iPhone secondary video or maneuver content into a separate ClarityLink process while stock Honda Type110, audio and controls remain intact. P4 production ingress implementation stays blocked. This is a bounded engineering decision for the preserved artifacts, not a judgment that a custom receiver or the whole project is impossible. P2 Display 1 research and separately authorized P3 recovery may continue on their own evidence gates. P1-C6 has not begun.

Starting HEAD `dc5d045bfacfcd5bc21b83d822f71b4f4c75df9e`; repository `bmreyes25/ClarityLink`, PR #19. This decision consumes the completed [P1-C1 ownership](p1c1-stock-session-ownership.md), [P1-C2 additive-seam](p1c2-jmcs-additive-extension-audit.md), [P1-C3 route-guidance](p1c3-iap2-route-guidance-ingress.md), and [P1-C4 coexistence](p1c4-independent-receiver-coexistence.md) audits and their matrices. It does not repeat the frozen firmware callgraphs. The machine-readable [decision record](p1c5-ingress-decision.json) names the seven architectures, 12 gates per candidate, source evidence, dependencies and rankings. [Evidence-gate rules](p1c5-evidence-gates.md) describe the engine's conservative interpretation.

## What the four investigations established

Stock `jmcs` owns Honda USB/iAP2, factory authentication, CarPlay control, Type110 and its security state. Its reviewed SETUP path skips Type111. No supported external Type111, session-security handoff or authenticated maneuver subscriber was found. The declared navigation Binder callback carries two booleans. Honda-native route structures cannot be relabeled as Apple Maps or Waze; the preserved route response sender itself is unverified. The PlayPort 43P real-iPhone trace establishes one experimental receiver with two streams, not ClarityLink/Honda coexistence. ClarityLink's host receiver, native decode, Android API17 adapters and simulators remain useful code and test assets. No real ClarityLink iPhone session or Display 1 admission was established.

## Decision comparison

| Architecture | Original-goal fit if proven | Evidence today; implementation gate |
|---|---|---|
| **A — stock session delegates Type111** | Full secondary map candidate with least disruption to stock Type110 | **Conditional.** Honda `/info`/SETUP contribution, endpoint/security delegation and teardown ABI absent. No production implementation. |
| **B — stock session exports iAP2 guidance** | Authentic maneuver-only candidate, not a full live map | **Conditional.** Decoded active-app route payload, provenance and no-APK subscriber absent. |
| **C — Honda-native navigation service** | Does not satisfy active-iPhone source unless independently proven | Factory-navigation contract exists; CarPlay source and sender UID unverified. No promotion. |
| **D — two receivers on one wired/session path** | Could provide custom video only with Apple and iAP2 multiplex admission | No independent auth/control/session sharing contract. |
| **E — stock wired plus custom wireless** | Could provide custom video if concurrent session truly allowed | Apple guidance favors one active transport/session; distinct authority and audio/control isolation unproven. |
| **F — full custom receiver lab** | Oracle for one receiver/two streams, not Honda coexistence | PlayPort 43P observed real iPhone in its lab profile; ClarityLink receiver results are synthetic/replay. **Lab only.** |
| **G — independent iOS companion** | Own navigation possible; active Apple Maps/Waze route not established | Needs a separately approved app/data path; cannot be called the original goal. |

No eighth evidenced architecture was found. **Ranking if the required interfaces are later proved:** A, B, G, D, E, C, F. This ranking weights stock-preserving ownership and integration risk ahead of full-map fidelity: B is maneuver-only, G may supply a different route, while D/E could supply video only after much heavier session and audio-isolation proof. **Ranking by useful evidence today:** F, C, A, B, G, D, E. F is a lab oracle and C is Honda-native only; **none is a deployable answer**. These are ordinal research priorities, not invented confidence scores.

## Decision tool and proof boundaries

The [standalone engine](../../src/carplay-session-model/ingress_decision.py) reads a versioned manifest, verifies exact catalog records and source-report SHA-256, evaluates the existing [ownership model](../../src/carplay-session-model/receiver_ownership.py), and returns separate fields for model consistency, interface sufficiency, live validation, implementation support, deployment eligibility and original-goal validation. Current positive interface, Honda-live, active-app and Display 1 proof catalogs are deliberately empty. A JSON flag, even `PROVEN`, cannot add a positive proof. Synthetic fixtures, other-receiver real-iPhone evidence, an emulator, and host tests cannot turn a candidate deployable. New evidence requires an independently reviewed catalog/code update; this tool is an offline decision aid, not a credential/signature verifier or runtime feature switch. Its default-deny result cannot authorize vehicle work.

## Single next evidence task

**Find and provenance-verify an OEM-supported, build-compatible Honda receiver extension contract** that explicitly binds secondary-display `/info`, Type111 SETUP/response, media endpoint and per-stream security to the existing authenticated session, with caller permission and teardown semantics. This is a *new artifact* question, not another broad scan of the same `jmcs`/proxy files. A complete contract could move A from conditional to independently testable and would directly change the architecture ranking; failure to obtain one keeps P4 production ingress blocked. The smallest experiment is offline source/artifact acquisition and hash/version/ABI review. No Honda or iPhone session is needed for that first step. Any later live test needs fresh, narrow authorization.

## Reusable work and permitted continuation

| Existing component | Classification | Safe next use |
|---|---|---|
| Type110/111 negotiation model, screen parser, transport and H.264 tests | `READY_FOR_REUSE` | Maintain regression fixtures and failure isolation offline. |
| Session-generation registry, authentication handoff interface, native receiver | `REUSABLE_AFTER_INGRESS_PROOF` | Use for a reviewed endpoint or separate lawful lab; never claim Honda's session from a pointer. |
| PlayPort/ClarityLink synthetic receiver harnesses | `OFFLINE_ONLY` | Compare sanitized one-receiver stream behavior; do not call it Honda validation. |
| Android API17 JNI/Surface and Display 1 adapters | `NEEDS_ADAPTATION` | Continue independent Display 1 admission and resource research. |
| Stock Type111/media/security bridge and iAP2 maneuver adapter | `BLOCKED_BY_INTERFACE` | Do not implement a production path until its actual source/permission contract exists. |
| New independent second receiver beside stock | `UNNECESSARY_FOR_SELECTED_BRANCH` | Retain as research only unless Apple/session coexistence evidence reverses the gate. |

No production Type111 implementation, stock-facing integration, Honda APK installation or session activation follows from this milestone. The P1-C6 handoff is the JSON gate record, the two rankings, the no-go conditions above, and the single new-artifact task.
