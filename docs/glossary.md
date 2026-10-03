# ClarityLink glossary

Terms below describe the project and its evidence. A model name or protocol label does not imply that the feature is available on the Honda.

| Term | Meaning |
|---|---|
| **Display 0** | The factory center display and its normal CarPlay experience. |
| **Display 1** | The proposed secondary display role intended for the cluster's existing Navigation region. Its Honda integration is unproven. |
| **Type110** | The Honda-confirmed stock CarPlay screen stream type. ClarityLink's design invariant is to preserve it. |
| **Type111** | A proposed secondary-screen stream type supported by some external implementations and observed in a separate current-iOS lab. Honda acceptance, schema, transport, and security remain unknown. |
| **AltScreen** | A CarPlay secondary-screen capability/protocol family. External prior art informs questions, not Honda requirements. |
| **ScreenStream** | The screen-media stream representation used by the modeled receiver path. Synthetic fixture behavior is not Honda runtime proof. |
| **`jmcs`** | Honda's examined CarPlay-related executable. Claims about it are scoped to the exact firmware artifact/hash in the linked evidence. |
| **Display Audio** | The vehicle's display/audio host environment examined in platform research. The real frame handoff to its cluster UI is unresolved. |
| **Cluster Navigation region** | Existing instrument-cluster area intended for navigation presentation; other stock cluster/safety UI must remain unaffected. |
| **SETUP** | CarPlay stream setup request/response exchange. The offline models do not establish Honda acceptance of Type111. |
| **`streamConnectionID`** | Identifier associated with a CarPlay stream connection. Its use for independent Honda Type111 crypto/lifecycle is unproven. |
| **`dataPort`** | Port value associated with a screen stream. A synthetic/model value is not a Honda-observed listener address or port. |
| **ViewArea** | A region/control concept found in external secondary-display material. Honda field requirements are unknown. |
| **SafeArea** | A geometry concept that describes content-safe bounds in some external implementations. Honda semantics remain unknown. |
| **Generation** | A project-model identifier used to distinguish successive synthetic stream lifetimes and reject stale cleanup. Honda has no proven corresponding project-generation contract. |
| **Type110 preservation** | Invariant that a separate Type111 failure or cleanup must not alter stock Type110, center-display, audio, or safety UI state. This is a design/test invariant, not runtime proof. |
| **Evidence classification** | A label describing claim provenance and scope. See [the full classification guide](development/evidence-classification.md). |
| **Honda runtime evidence** | Evidence collected from actual Honda runtime behavior, distinct from static firmware analysis, external prior art, and synthetic tests. |

For curated navigation, see the [documentation hub](README.md). For detailed claims, see the [evidence index](../EVIDENCE_INDEX.md).
