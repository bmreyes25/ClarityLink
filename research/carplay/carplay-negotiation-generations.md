# CarPlay capability generations

| Generation | Mechanism | Evidence boundary |
|---|---|---|
| Legacy receiver `/info` | phone-facing response with `features` and `displays[]`; Honda confirms one display dictionary with geometry, maxFPS, UUID, feature bits | Exact Honda keys are in `honda-info-capabilities.md`; bit semantics unresolved. |
| R15 / iOS 13 second-screen vehicle support | multiple H.264 streams, instrument-cluster content, ViewArea/SafeArea | Apple documents capability; Honda implementation unknown. |
| Modern Setup FeatureKey tokens | tokens such as `altScreen`/`viewAreas` appear in current prior art | Newer behavior; exact iOS compatibility and Honda parser support unknown. |
| iOS 27/current additions | current reverse engineering may describe additional tokens/semantics | Not evidence of legacy Honda requirement. |

Keep `/info`, R15-era second-screen behavior, and modern Setup feature arrays separate. Honda exact jmcs scan/build evidence found no `FeatureKey`, `altScreen`, `viewAreas`, `initialViewArea`, or `enabledFeatures` literal. Numeric `features` is separate and uninterpreted. Absence of strings does not rule out generated/generic fields.
