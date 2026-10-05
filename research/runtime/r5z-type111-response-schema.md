# R5Z Type111 response schema

| Field / behavior | Evidence | Host implementation | Honda status |
|---|---|---|---|
| Type111 request | `CURRENT_IOS_LAB_CONFIRMED` in 43P | accepts `type=111` | stock skips |
| distinct `streamConnectionID` | `CURRENT_IOS_LAB_CONFIRMED` | strict uint64 and uniqueness | Type111 use unknown |
| separate `dataPort` | `CURRENT_IOS_LAB_CONFIRMED` in PlayPort; `HONDA_TYPE110_ANALOG` | actual loopback assigned port | Type111 response unknown |
| cloned request fields | `EXTERNAL_PRIOR_ART` MHI2 | retained in lab response | unknown |
| `streamID=111` | `EXTERNAL_PRIOR_ART` MHI2 | lab profile only | unknown |
| complete `/info` profile | partial current lab and public receiver prior art | minimal fixture only | unknown |

The response is fully built before `plistlib` serialization. Successful host serialization does not imply an iPhone or Honda will accept the schema. Source: [43P observation](../lab/current-ios-type111-observation.md), [response model](../carplay/type111-response-model.md). Public comparisons: [xcertplay](https://github.com/shilapi/xcertplay), [MHI2](https://github.com/harman-f/mhi2_altscreen_carplay).
