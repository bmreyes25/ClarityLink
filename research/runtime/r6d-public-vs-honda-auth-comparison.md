# R6D public architecture versus Honda static evidence

| Behavior | Public expectation | Honda evidence | Result |
|---|---|---|---|
| Certificate | [Apple](https://support.apple.com/guide/security/verifying-accessories-sec70a4f377d/web): hardware IC supplies certificate | `APSMFiPlatform_CopyCertificate` → proxy → factory I²C | Match, static |
| Challenge/signature | Apple: IC signs challenge | `APSMFiPlatform_CreateSignature` → proxy; `uwh_ipod_cp_set_challenge/get_signature` | Match, static |
| Protocol/version | [xcertplay](https://github.com/shilapi/xcertplay/blob/master/README.md) exposes authenticator abstraction | Honda `get_auth_level`; correspondence to protocol major unknown | Partial |
| Lifecycle | [OCBM](https://github.com/lvalen91/ocbm) separates authentication component | Honda acquire/release and mutex around singleton fd | Structural match; cross-process use unknown |
| Second secure association | Apple describes MFi-SAP for CarPlay video | `APSMFiSAP_Exchange` calls factory certificate/signature platform functions | Match, static |

Public prior art guided questions only. Honda conclusions use Honda code/config evidence independently. No GPL code, proprietary specification text, real credential or register map is included.
