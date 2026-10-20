# R6E /info field readiness

No current-iOS ClarityLink exchange exists. R6B's shape is preserved; synthetic values in tests are not accepted as real values. The lab profile loader requires explicit evidence labels for every family and a complete shape. Its label check is a provenance gate for operator-supplied data, not verification of the underlying claim.

| Family | Current provenance | Real attempt readiness |
|---|---|---|
| device identity | INFERRED locally generated ID; physical correlation UNKNOWN | stable private file available; authority link UNKNOWN |
| receiver identity/name/model/manufacturer | EXTERNAL_PRIOR_ART shape | selected authority's lawful values required |
| display UUID/type 110/111 | CURRENT_IOS_LAB_CONFIRMED topology; EXTERNAL_PRIOR_ART shape | geometry/acceptance UNKNOWN |
| screen modes/resources | EXTERNAL_PRIOR_ART | chosen stack compatibility UNKNOWN |
| audio formats/latencies | EXTERNAL_PRIOR_ART field family | actual Mac route descriptors UNKNOWN |
| HID/input | EXTERNAL_PRIOR_ART field family | actual attached input/report descriptor UNKNOWN |
| feature bits/status flags | EXTERNAL_PRIOR_ART | accepted bitset UNKNOWN |
| protocol/source version | EXTERNAL_PRIOR_ART | real negotiated version UNKNOWN |
| timing/keepalive | HONDA_ANALOG and EXTERNAL_PRIOR_ART | transport-dependent behavior UNKNOWN |
| secondary display/initial URL/safe area | CURRENT_IOS_LAB_CONFIRMED two-display request topology; EXTERNAL_PRIOR_ART field shape | exact dimensions/acceptance UNKNOWN |

No unknown value is added to `InfoProfile` to force a successful response. In particular, phone `altScreenURLs` and SETUP `enabledFeatures` are not copied into receiver `/info`. A real attempt remains blocked by authority and the unsupported field values above. Differential tooling reports paths/types/counts only.
